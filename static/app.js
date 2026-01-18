(() => {
  const messageHost = document.getElementById("js-messages");
  const page = document.body.dataset.page || "";

  const showMessage = (text, kind = "success") => {
    if (!messageHost) {
      return;
    }
    const item = document.createElement("div");
    item.className = `flash ${kind}`;
    item.textContent = text;
    messageHost.appendChild(item);
    setTimeout(() => {
      item.remove();
    }, 4000);
  };

  const postJSON = async (url, payload) => {
    const response = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.error || "Request failed");
    }
    return data;
  };

  const getJSON = async (url) => {
    const response = await fetch(url);
    if (!response.ok) {
      throw new Error("Request failed");
    }
    return response.json();
  };

  const wireForm = (formSelector, endpoint, onSuccess) => {
    const form = document.querySelector(formSelector);
    if (!form) {
      return;
    }
    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      const payload = Object.fromEntries(new FormData(form).entries());
      try {
        const created = await postJSON(endpoint, payload);
        form.reset();
        showMessage("Saved successfully.", "success");
        if (onSuccess) {
          onSuccess(created);
        }
      } catch (error) {
        showMessage(error.message, "error");
      }
    });
  };

  const renderPatients = (patients) => {
    const body = document.getElementById("patients-body");
    if (!body) {
      return;
    }
    body.innerHTML = "";
    if (!patients.length) {
      body.innerHTML =
        '<tr><td colspan="6" class="muted">No patients yet.</td></tr>';
      return;
    }
    patients.forEach((patient) => {
      const row = document.createElement("tr");
      row.innerHTML = `
        <td>${patient.id}</td>
        <td>${patient.name}</td>
        <td>${patient.age}</td>
        <td>${patient.gender}</td>
        <td>${patient.contact || ""}</td>
        <td>${patient.created_at}</td>
      `;
      body.appendChild(row);
    });
  };

  const renderAppointments = (appointments) => {
    const body = document.getElementById("appointments-body");
    if (!body) {
      return;
    }
    body.innerHTML = "";
    if (!appointments.length) {
      body.innerHTML =
        '<tr><td colspan="6" class="muted">No appointments yet.</td></tr>';
      return;
    }
    appointments.forEach((appointment) => {
      const row = document.createElement("tr");
      row.innerHTML = `
        <td>${appointment.id}</td>
        <td>${appointment.patient_name} (${appointment.patient_id})</td>
        <td>${appointment.date}</td>
        <td>${appointment.time}</td>
        <td>${appointment.reason}</td>
        <td>${appointment.status}</td>
      `;
      body.appendChild(row);
    });
  };

  const renderBills = (bills) => {
    const body = document.getElementById("billing-body");
    if (!body) {
      return;
    }
    body.innerHTML = "";
    if (!bills.length) {
      body.innerHTML =
        '<tr><td colspan="6" class="muted">No billing records yet.</td></tr>';
      return;
    }
    bills.forEach((bill) => {
      const row = document.createElement("tr");
      row.innerHTML = `
        <td>${bill.id}</td>
        <td>${bill.patient_name} (${bill.patient_id})</td>
        <td>${bill.description}</td>
        <td>${bill.amount}</td>
        <td>${bill.status}</td>
        <td>${bill.created_at}</td>
      `;
      body.appendChild(row);
    });
  };

  const refreshOverview = async () => {
    try {
      const data = await getJSON("/api/overview");
      const map = {
        "total-patients": data.patients,
        "total-appointments": data.appointments,
        "total-bills": data.bills,
        "total-unpaid": data.unpaid,
      };
      Object.entries(map).forEach(([id, value]) => {
        const node = document.getElementById(id);
        if (node) {
          node.textContent = value;
        }
      });
    } catch (error) {
      showMessage("Unable to refresh overview.", "error");
    }
  };

  const refreshPatients = async () => {
    try {
      const patients = await getJSON("/api/patients");
      renderPatients(patients);
    } catch (error) {
      showMessage("Unable to refresh patients.", "error");
    }
  };

  const refreshAppointments = async () => {
    try {
      const appointments = await getJSON("/api/appointments");
      renderAppointments(appointments);
    } catch (error) {
      showMessage("Unable to refresh appointments.", "error");
    }
  };

  const refreshBills = async () => {
    try {
      const bills = await getJSON("/api/bills");
      renderBills(bills);
    } catch (error) {
      showMessage("Unable to refresh billing records.", "error");
    }
  };

  if (page === "index") {
    refreshOverview();
    setInterval(refreshOverview, 5000);
  }

  if (page === "patients") {
    wireForm("form", "/api/patients", refreshPatients);
    refreshPatients();
    setInterval(refreshPatients, 7000);
  }

  if (page === "appointments") {
    wireForm("form", "/api/appointments", refreshAppointments);
    refreshAppointments();
    setInterval(refreshAppointments, 7000);
  }

  if (page === "billing") {
    wireForm("form", "/api/bills", refreshBills);
    refreshBills();
    setInterval(refreshBills, 7000);
  }
})();
