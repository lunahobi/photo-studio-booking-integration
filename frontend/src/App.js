import React, { useState } from "react";
import axios from "axios";

function App() {
  const [availabilityParams, setAvailabilityParams] = useState({
    hallId: "hall-001",
    startDate: "",
    endDate: "",
  });
  const [slots, setSlots] = useState([]);
  const [selectedSlot, setSelectedSlot] = useState(null);

  const [booking, setBooking] = useState(null);
  const [bookingForm, setBookingForm] = useState({
    customerName: "Иван Иванов",
    customerEmail: "ivan@example.com",
    customerPhone: "+79161234567",
  });

  const [payment, setPayment] = useState(null);
  const [loading, setLoading] = useState(false);
  const [log, setLog] = useState("");

  const appendLog = (msg) => setLog((prev) => prev + msg + "\n");

  // Преобразование времени слота в ISO без Z (offset-naive)
  const toNaiveIso = (s) => {
    const d = new Date(s);
    return d.toISOString().replace(/\.\d{3}Z$/, "");
  };

  // 1) Доступность
  const loadSlots = async () => {
    try {
      if (!availabilityParams.startDate || !availabilityParams.endDate) {
        appendLog("Ошибка доступности: нужно заполнить start_date и end_date");
        return;
      }

      setLoading(true);
      setSlots([]);
      setSelectedSlot(null);
      appendLog("Запрос доступности...");

      const resp = await axios.get("/api/bookings/availability", {
        params: {
          hall_id: availabilityParams.hallId,
          start_date: availabilityParams.startDate,
          end_date: availabilityParams.endDate,
        },
      });

      const data = resp.data || {};
      const slotsResp = data.slots || [];
      setSlots(slotsResp);
      appendLog(`Найдено слотов: ${slotsResp.length}`);
    } catch (e) {
      console.error("Availability error:", e);
      const err = e.response?.data?.error || e.response?.data || e.message || "Unknown error";
      appendLog("Ошибка доступности: " + (typeof err === "string" ? err : JSON.stringify(err)));
    } finally {
      setLoading(false);
    }
  };

  // 2) Создание брони
  const createBooking = async () => {
    if (!selectedSlot) {
      alert("Сначала выберите слот");
      return;
    }
    try {
      setLoading(true);
      appendLog("Создание брони...");

      const startRaw = selectedSlot.start_time || selectedSlot.startTime;
      const endRaw = selectedSlot.end_time || selectedSlot.endTime;

      const resp = await axios.post("/api/bookings", {
        hall_id: availabilityParams.hallId,
        user_id: "user-123",
        start_time: toNaiveIso(startRaw),
        end_time: toNaiveIso(endRaw),
        customer_name: bookingForm.customerName,
        customer_email: bookingForm.customerEmail,
        customer_phone: bookingForm.customerPhone,
      });

      setBooking(resp.data);
      setPayment(null);
      appendLog(
        `Бронь создана: ${resp.data.booking_id}, статус: ${resp.data.status}`
      );
    } catch (e) {
      const err =
        e.response?.data?.error ||
        e.response?.data?.detail ||
        e.message;
      appendLog("Ошибка бронирования: " + err);
    } finally {
      setLoading(false);
    }
  };

  // 3) Создание платежа
  const createPayment = async () => {
    if (!booking) {
      alert("Сначала создайте бронь");
      return;
    }
    try {
      setLoading(true);
      appendLog("Создание платежа...");

      const resp = await axios.post("/api/payments", {
        booking_id: booking.booking_id,
        amount: parseFloat(booking.total_amount),
        payment_type: "full_payment",
        payment_method: "yookassa",
      });

      setPayment(resp.data);
      appendLog(
        `Платеж создан: ${resp.data.payment_id}, статус: ${resp.data.status}`
      );
      appendLog(`URL оплаты: ${resp.data.payment_url}`);
    } catch (e) {
      const err =
        e.response?.data?.error ||
        e.response?.data?.detail ||
        e.message;
      appendLog("Ошибка платежа: " + err);
    } finally {
      setLoading(false);
    }
  };

  // 4) Симуляция успешной оплаты (webhook + обновление статусов)
  const simulateSuccess = async () => {
    if (!payment || !booking) {
      alert("Нужны и бронь, и платеж");
      return;
    }
    try {
      setLoading(true);
      appendLog("Отправка webhook payment.succeeded...");

      const webhookPayload = {
        type: "notification",
        event: "payment.succeeded",
        object: {
          id: payment.external_payment_id,
          status: "succeeded",
          amount: {
            value: String(payment.amount),
            currency: "RUB",
          },
          metadata: {
            booking_id: booking.booking_id,
          },
        },
        created_at: new Date().toISOString(),
      };

      // Webhook идёт напрямую в Payment Service (порт 5002)
      await axios.post(
        "http://localhost:5002/api/payments/webhook/yookassa",
        webhookPayload
      );

      appendLog("Webhook обработан, обновляем статусы...");

      const [payResp, bookResp] = await Promise.all([
        axios.get(`/api/payments/${payment.payment_id}`),
        axios.get(`/api/bookings/${booking.booking_id}`),
      ]);

      setPayment(payResp.data);
      setBooking(bookResp.data);

      appendLog(`Статус платежа: ${payResp.data.status}`);
      appendLog(`Статус брони: ${bookResp.data.status}`);
    } catch (e) {
      const err =
        e.response?.data?.error ||
        e.response?.data?.detail ||
        e.message;
      appendLog("Ошибка webhook/обновления: " + err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ maxWidth: 1000, margin: "0 auto", fontFamily: "sans-serif" }}>
      <h1>Система бронирования фотостудии (frontend)</h1>

      {/* 1. Доступность */}
      <section style={{ border: "1px solid #ccc", padding: 16, marginBottom: 16 }}>
        <h2>1. Проверка доступности</h2>
        <div>
          <label>
            Зал:
            <input
              value={availabilityParams.hallId}
              onChange={(e) =>
                setAvailabilityParams((p) => ({ ...p, hallId: e.target.value }))
              }
              style={{ marginLeft: 8 }}
            />
          </label>
        </div>
        <div>
          <label>
            Начало (ISO):
            <input
              style={{ marginLeft: 8, width: 260 }}
              placeholder="2025-12-20T00:00:00"
              value={availabilityParams.startDate}
              onChange={(e) =>
                setAvailabilityParams((p) => ({ ...p, startDate: e.target.value }))
              }
            />
          </label>
        </div>
        <div>
          <label>
            Конец (ISO):
            <input
              style={{ marginLeft: 8, width: 260 }}
              placeholder="2025-12-21T00:00:00"
              value={availabilityParams.endDate}
              onChange={(e) =>
                setAvailabilityParams((p) => ({ ...p, endDate: e.target.value }))
              }
            />
          </label>
        </div>
        <button onClick={loadSlots} disabled={loading} style={{ marginTop: 8 }}>
          Загрузить слоты
        </button>

        {slots.length > 0 && (
          <div style={{ marginTop: 12, maxHeight: 200, overflowY: "auto" }}>
            <p>Найдено слотов: {slots.length}</p>
            <table border="1" cellPadding="4">
              <thead>
                <tr>
                  <th>Начало</th>
                  <th>Конец</th>
                  <th>Доступен</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {slots.map((s, idx) => (
                  <tr key={idx}>
                    <td>{s.start_time || s.startTime}</td>
                    <td>{s.end_time || s.endTime}</td>
                    <td>{String(s.available)}</td>
                    <td>
                      {s.available && (
                        <button onClick={() => setSelectedSlot(s)}>
                          Выбрать
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {selectedSlot && (
              <p style={{ marginTop: 8 }}>
                Выбран слот: {selectedSlot.start_time || selectedSlot.startTime} →
                {selectedSlot.end_time || selectedSlot.endTime}
              </p>
            )}
          </div>
        )}
      </section>

      {/* 2. Бронирование */}
      <section style={{ border: "1px solid #ccc", padding: 16, marginBottom: 16 }}>
        <h2>2. Создание бронирования</h2>
        <div>
          <label>
            Имя:
            <input
              style={{ marginLeft: 8, width: 220 }}
              value={bookingForm.customerName}
              onChange={(e) =>
                setBookingForm((p) => ({ ...p, customerName: e.target.value }))
              }
            />
          </label>
        </div>
        <div>
          <label>
            Email:
            <input
              style={{ marginLeft: 8, width: 220 }}
              value={bookingForm.customerEmail}
              onChange={(e) =>
                setBookingForm((p) => ({ ...p, customerEmail: e.target.value }))
              }
            />
          </label>
        </div>
        <div>
          <label>
            Телефон:
            <input
              style={{ marginLeft: 8, width: 220 }}
              value={bookingForm.customerPhone}
              onChange={(e) =>
                setBookingForm((p) => ({ ...p, customerPhone: e.target.value }))
              }
            />
          </label>
        </div>
        <button
          onClick={createBooking}
          disabled={loading || !selectedSlot}
          style={{ marginTop: 8 }}
        >
          Создать бронь для выбранного слота
        </button>

        {booking && (
          <div style={{ marginTop: 8 }}>
            <p>Booking ID: {booking.booking_id}</p>
            <p>Статус: {booking.status}</p>
            <p>Сумма: {booking.total_amount}</p>
          </div>
        )}
      </section>

      {/* 3. Оплата */}
      <section style={{ border: "1px solid #ccc", padding: 16, marginBottom: 16 }}>
        <h2>3. Оплата и статусы</h2>
        <button onClick={createPayment} disabled={loading || !booking}>
          Создать платёж
        </button>
        <button
          onClick={simulateSuccess}
          disabled={loading || !payment || !booking}
          style={{ marginLeft: 8 }}
        >
          Симулировать успешную оплату
        </button>

        {payment && (
          <div style={{ marginTop: 8 }}>
            <p>Payment ID: {payment.payment_id}</p>
            <p>Статус платежа: {payment.status}</p>
            <p>
              Payment URL:{" "}
              <a href={payment.payment_url} target="_blank" rel="noreferrer">
                {payment.payment_url}
              </a>
            </p>
          </div>
        )}

        {booking && (
          <div style={{ marginTop: 8 }}>
            <p>Текущий статус брони: {booking.status}</p>
          </div>
        )}
      </section>

      {/* Лог */}
      <section style={{ border: "1px solid #ccc", padding: 16 }}>
        <h2>Лог</h2>
        <pre
          style={{
            background: "#f5f5f5",
            maxHeight: 200,
            overflowY: "auto",
            padding: 8,
          }}
        >
          {log || "Здесь будут появляться шаги и ошибки"}
        </pre>
      </section>

      {loading && <p>Выполняется запрос...</p>}
    </div>
  );
}

export default App;
