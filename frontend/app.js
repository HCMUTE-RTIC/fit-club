"use strict";
const $ = (id) => document.getElementById(id);
const all = (selector) => [...document.querySelectorAll(selector)];
const state = {
  token: sessionStorage.getItem("fit-token") || "",
  me: null,
  events: [],
  clubs: [],
  event: null,
  club: null,
  view: "overview",
  offset: 0,
  total: 0,
  epoch: 0,
  stream: null,
  cameraRun: 0,
  scanBusy: false,
  qrRun: 0,
  qrTimer: null,
  qrWanted: false,
  studentEmailOnly: true,
};
const views = {
  overview: [
    "Tổng quan",
    "Tổng quan sự kiện",
    "Mỗi kết nối là một khởi đầu mới.",
  ],
  participants: [
    "Người tham gia",
    "Những gương mặt đồng hành",
    "Quản lý danh sách và kết quả tại gian hàng của bạn.",
  ],
  checkin: [
    "Quét điểm danh",
    "Chào đón những kết nối mới",
    "Một lần quét, thêm một dấu ấn tại gian hàng.",
  ],
  ticket: [
    "Vé của tôi",
    "Hành trình của bạn",
    "Sẵn sàng khám phá và kết nối cùng các câu lạc bộ.",
  ],
  settings: [
    "Quản trị",
    "Cùng tạo nên ngày hội",
    "Điều phối sự kiện, gian hàng và đội ngũ quản trị.",
  ],
};
let noticeTimer,
  decoderPromise,
  personAction,
  editingEvent = false,
  confirmAction;
const number = (value) => new Intl.NumberFormat("vi-VN").format(value);
const dateTime = (value) =>
  value
    ? new Date(value).toLocaleString("vi-VN", {
        timeZone: "Asia/Ho_Chi_Minh",
        hour: "2-digit",
        minute: "2-digit",
        day: "2-digit",
        month: "2-digit",
        year: "numeric",
      })
    : "—";
const initials = (name) =>
  String(name || "?")
    .trim()
    .split(/\s+/)
    .slice(-2)
    .map((part) => part[0])
    .join("")
    .toUpperCase();
const superUser = () => state.me?.role === "superadmin";
const manager = () => Boolean(state.club?.can_manage);
const eventPath = () => {
  if (!state.event) throw Error("Chọn sự kiện trước.");
  return "/events/" + state.event.id;
};
const clubPath = () => {
  if (!state.club) throw Error("Chọn một gian hàng CLB trước.");
  return eventPath() + "/clubs/" + state.club.id;
};
function node(tag, className, text) {
  const element = document.createElement(tag);
  if (className) element.className = className;
  if (text !== undefined) element.textContent = text;
  return element;
}
function icon(name, className = "") {
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("class", "icon " + className);
  svg.setAttribute("aria-hidden", "true");
  const use = document.createElementNS(svg.namespaceURI, "use");
  use.setAttribute("href", "#i-" + name);
  svg.append(use);
  return svg;
}
// Use the supplied identity assets for known clubs; other clubs keep their own initials.
function clubMark(name) {
  const key = String(name || "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase();
  let filename, label;
  if (/\brtic\b/.test(key)) {
    filename = "/assets/brand/rtic.png";
    label = "RTIC";
  } else if (/\bdsc\b|developer student club/.test(key)) {
    filename = "/assets/brand/dsc.png";
    label = "DSC";
  } else if (/\bisc\b|\battt\b|an toan thong tin/.test(key)) {
    filename = "/assets/brand/isc.png";
    label = name;
  } else if (!name) {
    filename = "/assets/bo-logo/ban-cat-goc/09-club-day-2026.png";
    label = "FIT Club Day 2026";
  }
  const mark = node("span", "club-logo");
  const fallback = () => {
    mark.replaceChildren(
      node("span", "club-initials", name?.length <= 5 ? name : initials(name)),
    );
    mark.setAttribute("role", "img");
    mark.setAttribute("aria-label", name || "FIT Club Day");
  };
  if (filename) {
    const image = node("img");
    image.src = filename;
    image.alt = "Logo " + label;
    image.width = 120;
    image.height = 96;
    image.onerror = fallback;
    mark.append(image);
  } else fallback();
  return mark;
}
function updateClubMark(id, name) {
  const target = $(id),
    key = name || "fit-club-day";
  if (target.dataset.brand === key) return;
  target.dataset.brand = key;
  target.replaceChildren(clubMark(name));
}
function notice(message, error = false) {
  $("notice-message").textContent = message;
  $("notice").classList.toggle("error", error);
  $("notice").hidden = false;
  clearTimeout(noticeTimer);
  noticeTimer = setTimeout(
    () => ($("notice").hidden = true),
    error ? 10000 : 6000,
  );
}
function errorText(detail) {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail))
    return detail
      .map((item) => {
        const labels = {
          name: "Họ tên / tên CLB",
          email: "Email",
          title: "Tên sự kiện",
          starts_at: "Thời gian",
          image_url: "Ảnh",
        };
        const field = item.loc?.at(-1);
        return (labels[field] || field || "Dữ liệu") + ": " + item.msg;
      })
      .join("\n");
  return "Không thể hoàn tất thao tác. Vui lòng thử lại.";
}
async function api(path, options = {}) {
  const token = state.token,
    headers = new Headers(options.headers || {});
  if (token) headers.set("Authorization", "Bearer " + token);
  const request = { ...options, headers, cache: "no-store" };
  if (options.json !== undefined) {
    headers.set("Content-Type", "application/json");
    request.body = JSON.stringify(options.json);
    delete request.json;
  }
  let response;
  try {
    response = await fetch(path, request);
  } catch {
    throw Error("Không kết nối được máy chủ. Kiểm tra mạng và thử lại.");
  }
  if (!response.ok) {
    let message = "Máy chủ chưa xử lý được yêu cầu (" + response.status + ").";
    try {
      message = errorText((await response.json()).detail);
    } catch {}
    if (
      response.status === 401 &&
      path !== "/auth/google" &&
      token === state.token
    ) {
      logout();
      message = "Phiên đăng nhập đã hết hạn. Đăng nhập Google để tiếp tục.";
    }
    const error = new Error(message);
    error.status = response.status;
    throw error;
  }
  if (response.status === 204) return null;
  return response.headers.get("content-type")?.includes("application/json")
    ? response.json()
    : response.blob();
}
function guarded(action) {
  return async (event) => {
    event?.preventDefault?.();
    const button =
      event?.currentTarget instanceof HTMLButtonElement
        ? event.currentTarget
        : null;
    if (button?.disabled || button?.dataset.busy) return;
    if (button) {
      button.dataset.busy = "true";
      button.setAttribute("aria-busy", "true");
    }
    try {
      await action(event);
    } catch (error) {
      notice(error.message, true);
    } finally {
      if (button) {
        delete button.dataset.busy;
        button.removeAttribute("aria-busy");
      }
    }
  };
}
function bindForm(id, action) {
  $(id).addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = event.currentTarget,
      button = form.querySelector('button:not([type="button"])');
    if (button.disabled) return;
    button.disabled = true;
    const errorBox = form.querySelector(".form-error");
    if (errorBox) errorBox.hidden = true;
    try {
      await action(new FormData(form), form);
    } catch (error) {
      if (errorBox && form.closest("dialog")?.open) {
        errorBox.textContent = error.message;
        errorBox.hidden = false;
      } else notice(error.message, true);
    } finally {
      button.disabled = false;
    }
  });
}
function openDialog(id, reset = true) {
  const dialog = $(id);
  if (reset) dialog.querySelector("form")?.reset();
  const error = dialog.querySelector(".form-error");
  if (error) error.hidden = true;
  dialog.showModal();
}
function logout() {
  state.epoch++;
  stopCamera();
  clearQr();
  state.token = "";
  state.me = null;
  state.event = null;
  state.club = null;
  state.events = [];
  state.clubs = [];
  sessionStorage.removeItem("fit-token");
  all("dialog[open]").forEach((dialog) => dialog.close());
  $("workspace").hidden = true;
  $("login").hidden = false;
  $("event-panel").hidden = true;
  $("loading").hidden = true;
  $("students").replaceChildren();
  $("recent-list").replaceChildren();
}
function applyPermissions() {
  all("[data-super]").forEach((element) => (element.hidden = !superUser()));
  all("[data-manager]").forEach((element) => (element.hidden = !manager()));
  $("add-admin").disabled = !state.club;
  if (
    (!manager() && ["participants", "checkin"].includes(state.view)) ||
    (!superUser() && state.view === "settings") ||
    (!state.club && state.view === "ticket")
  )
    state.view = "overview";
}
async function bootUser(preferred = {}) {
  const token = state.token,
    epoch = state.epoch;
  const identity = await api("/auth/me");
  if (token !== state.token || epoch !== state.epoch) return;
  state.me = identity;
  $("my-name").textContent = state.me.name;
  $("account-email").textContent = state.me.email;
  $("my-avatar").textContent = initials(state.me.name);
  $("my-role").textContent = {
    superadmin: "Ban tổ chức · Superadmin",
    admin: "Quản trị câu lạc bộ",
    student: "Người tham gia",
  }[state.me.role];
  $("login").hidden = true;
  $("workspace").hidden = false;
  await loadEvents(preferred);
}
function emptyState(title, message) {
  $("event-panel").hidden = true;
  $("empty-state").hidden = false;
  $("empty-title").textContent = title;
  $("empty-message").textContent = message;
  $("empty-action").textContent = state.event
    ? "Thêm gian hàng CLB"
    : "Tạo sự kiện đầu tiên";
}
async function workspaceEvents() {
  const assigned = await api("/events");
  if (state.me?.role !== "student") return assigned;
  const catalog = await api("/events/discover");
  return [
    ...new Map(
      [...catalog, ...assigned].map((item) => [item.id, item]),
    ).values(),
  ].sort((a, b) => new Date(b.starts_at) - new Date(a.starts_at));
}
async function workspaceClubs() {
  return api(
    eventPath() +
      (state.me?.role === "student" && state.event.checkin_open
        ? "/clubs/discover"
        : "/clubs"),
  );
}
async function loadEvents(preferred = {}) {
  const epoch = ++state.epoch,
    eventId = preferred.eventId ?? state.event?.id,
    clubId = preferred.clubId ?? state.club?.id;
  stopCamera();
  clearQr();
  $("loading").hidden = false;
  $("event-panel").hidden = true;
  $("page-error").hidden = true;
  $("empty-state").hidden = true;
  try {
    const events = await workspaceEvents();
    if (epoch !== state.epoch) return;
    state.events = events;
    state.event =
      events.find((item) => item.id === eventId) || events[0] || null;
    $("events").replaceChildren(
      ...events.map((item) => new Option(item.title, item.id)),
    );
    $("events").disabled = !events.length;
    if (!state.event) {
      state.club = null;
      state.clubs = [];
      $("clubs").replaceChildren(new Option("Chưa có CLB", ""));
      $("events").replaceChildren(new Option("Chưa có sự kiện đang mở", ""));
      $("clubs").disabled = true;
      applyPermissions();
      emptyState(
        "Chưa có sự kiện dành cho bạn",
        superUser()
          ? "Tạo sự kiện đầu tiên để bắt đầu kết nối các câu lạc bộ."
          : "Khi ban tổ chức mở sự kiện, bạn có thể xem các CLB và tự bấm Tham gia tại đây.",
      );
      return;
    }
    $("events").value = state.event.id;
    const clubs = await workspaceClubs();
    if (epoch !== state.epoch) return;
    state.clubs = clubs;
    state.club =
      clubs.find((item) => item.id === clubId) ||
      (state.me.role === "admin"
        ? clubs.find((item) => item.can_manage) || clubs[0] || null
        : null);
    const options = clubs.map((item) => new Option(item.name, item.id));
    if (superUser() || state.me.role === "student")
      options.unshift(new Option("Tất cả CLB", ""));
    if (!options.length) options.push(new Option("Chưa có CLB", ""));
    $("clubs").replaceChildren(...options);
    $("clubs").disabled = !clubs.length;
    $("clubs").value = state.club?.id || "";
    state.offset = 0;
    $("filter").reset();
    applyPermissions();
    renderContext();
    if (!clubs.length && !superUser() && !state.event.checkin_open) {
      emptyState(
        "Chưa có gian hàng dành cho bạn",
        "Ban tổ chức chưa mở gian hàng. Danh sách sẽ cập nhật khi CLB sẵn sàng.",
      );
      return;
    }
    $("event-panel").hidden = false;
    await showView(state.view);
  } catch (error) {
    if (epoch !== state.epoch) return;
    $("page-error").textContent = error.message + " Bấm Làm mới để tải lại.";
    $("page-error").hidden = false;
  } finally {
    if (epoch === state.epoch) $("loading").hidden = true;
  }
}
function renderContext() {
  if (!state.event) return;
  const open =
    state.event.checkin_open && (!state.club || state.club.checkin_open);
  $("event-title").textContent = state.event.title;
  updateClubMark("hero-club-brand", state.club?.name);
  updateClubMark("ticket-club-brand", state.club?.name);
  $("hero-brand-label").textContent = state.club
    ? "GIAN HÀNG ĐỒNG HÀNH"
    : "FIT CLUB DAY 2026";
  $("hero-subtitle").textContent = state.club
    ? state.club.name +
      " · " +
      (state.club.description || "Gian hàng kết nối cộng đồng công nghệ")
    : "Không gian chung của các câu lạc bộ học thuật HCMUTE";
  $("event-time").textContent = dateTime(state.event.starts_at);
  $("event-status").textContent = !state.club
    ? state.event.checkin_open
      ? "Sự kiện đang mở"
      : "Sự kiện đang đóng"
    : open
      ? "Đang mở điểm danh"
      : state.event.checkin_open
        ? "CLB chưa mở điểm danh"
        : "Sự kiện đang đóng";
  $("event-status").className = "badge" + (open ? "" : " neutral");
  $("progress-scope").textContent = state.club?.name || "Toàn sự kiện";
  $("registered-label").textContent = state.club
    ? "Người tham gia"
    : "Lượt đăng ký";
  $("attended-label").textContent = state.club
    ? "Đã điểm danh"
    : "Lượt điểm danh";
  $("scanner-club").textContent = state.club?.name || "";
  $("checkin-club-name").textContent = state.club?.name || "";
  $("toggle-club").textContent = state.club?.checkin_open
    ? "Tạm đóng điểm danh CLB"
    : "Mở điểm danh CLB";
  $("event-description").textContent =
    state.event.description || "Chưa có mô tả sự kiện.";
  $("toggle-event").textContent = state.event.checkin_open
    ? "Đóng sự kiện"
    : "Mở sự kiện";
  $("admins-title").textContent = state.club
    ? "Admin · " + state.club.name
    : "Admin CLB";
  $("manager-overview").hidden = !manager() && !superUser();
  $("student-overview").hidden = manager() || superUser();
  $("student-catalog").hidden = manager() || superUser();
  if (!manager() && !superUser()) renderStudentCatalog();
  $("ticket-club-name").textContent = state.club?.name || "Chọn gian hàng";
  $("ticket-event-title").textContent = state.event.title;
  $("ticket-name").textContent = state.me.name;
  $("ticket-student-id").textContent = "MSSV / mã: " + state.me.student_id;
  $("ticket-avatar").textContent = initials(state.me.name);
}
async function showView(view) {
  if (!views[view]) view = "overview";
  if (["participants", "checkin"].includes(view) && !manager())
    view = "overview";
  if (view === "settings" && !superUser()) view = "overview";
  if (view === "ticket" && !state.club) {
    const registered = state.clubs.find((item) => item.registered);
    if (registered) {
      state.club = registered;
      $("clubs").value = registered.id;
      renderContext();
    } else {
      notice("Chọn một CLB và bấm Tham gia để nhận vé cá nhân.");
      view = "overview";
    }
  }
  const previous = state.view;
  state.view = view;
  $("account-menu").open = false;
  if (view !== "checkin") stopCamera();
  if (view !== "ticket") clearQr();
  all("[data-view]").forEach(
    (element) => (element.hidden = element.dataset.view !== view),
  );
  all("[data-nav]").forEach((button) => {
    const active = button.dataset.nav === view;
    button.classList.toggle("active", active);
    if (active) button.setAttribute("aria-current", "page");
    else button.removeAttribute("aria-current");
  });
  $("breadcrumb").textContent = views[view][0];
  $("page-title").textContent = views[view][1];
  $("page-description").textContent = views[view][2];
  if (!state.event) return;
  if (view === "participants") await loadStudents();
  else if (view === "settings") await loadSettings();
  else if (view === "overview" && (manager() || superUser()))
    await loadSummary();
  else if (state.club && ["overview", "ticket"].includes(view))
    await loadMyStatus();
  if (previous !== view) $("main-content").focus({ preventScroll: true });
}
function filterQuery() {
  const data = new FormData($("filter")),
    query = new URLSearchParams();
  if (data.get("search")?.trim())
    query.set("search", data.get("search").trim());
  if (data.get("attended")) query.set("attended", data.get("attended"));
  return query;
}
function personCell(person) {
  const wrapper = node("div", "person-cell"),
    info = node("div", "person-info");
  info.append(node("strong", "", person.name), node("small", "", person.email));
  wrapper.append(node("span", "avatar", initials(person.name)), info);
  return wrapper;
}
async function loadStudents() {
  if (!manager()) return;
  const epoch = state.epoch,
    path = clubPath(),
    query = filterQuery();
  query.set("offset", state.offset);
  query.set("limit", 25);
  const data = await api(path + "/students?" + query);
  if (epoch !== state.epoch) return;
  state.total = data.total;
  $("students").replaceChildren(
    ...data.items.map((person) => {
      const row = node("tr"),
        who = node("td"),
        status = node("td"),
        checked = node("td");
      who.append(personCell(person));
      status.append(
        node(
          "span",
          "badge " + (person.attended ? "" : "neutral"),
          person.attended ? "Đã điểm danh" : "Chưa điểm danh",
        ),
      );
      checked.append(node("time", "", dateTime(person.checked_at)));
      row.append(who, node("td", "mono", person.student_id), status, checked);
      return row;
    }),
  );
  $("student-total").textContent = number(data.total);
  $("table-empty").hidden = data.items.length > 0;
  $("page").textContent = data.total
    ? data.offset +
      1 +
      "–" +
      (data.offset + data.items.length) +
      " trên " +
      number(data.total) +
      " người"
    : "0 người tham gia";
  $("page-number").textContent = Math.floor(data.offset / 25) + 1;
  $("prev").disabled = data.offset === 0;
  $("next").disabled = data.offset + data.items.length >= data.total;
}
async function loadSummary() {
  const epoch = state.epoch,
    path = state.club ? clubPath() : eventPath(),
    data = await api(path + "/summary");
  if (epoch !== state.epoch) return;
  for (const [id, key] of [
    ["stat-registered", "registered"],
    ["stat-attended", "attended"],
    ["stat-pending", "pending"],
    ["legend-attended", "attended"],
    ["legend-pending", "pending"],
  ])
    $(id).textContent = number(data[key]);
  $("stat-rate").textContent = number(data.rate) + "%";
  $("attendance-donut").style.setProperty(
    "--rate",
    Math.min(100, data.rate) + "%",
  );
  $("attendance-donut").setAttribute(
    "aria-label",
    data.rate + "% lượt đã điểm danh",
  );
  $("summary-note").textContent = state.club
    ? "Kết quả riêng của " +
      state.club.name +
      " · Cập nhật " +
      dateTime(new Date().toISOString())
    : data.clubs +
      " gian hàng · " +
      number(data.unique_attendees) +
      " sinh viên đã ghé · Mỗi sinh viên có thể ghé nhiều CLB";
  const recent = $("recent-list");
  recent.replaceChildren();
  $("activity-title").textContent = state.club
    ? "Vừa ghé gian hàng"
    : "Nhịp kết nối các CLB";
  if (data.club_summaries)
    data.club_summaries.slice(0, 6).forEach((club) => {
      const row = node("div", "recent-row"),
        info = node("div", "person-info");
      info.append(
        node("strong", "", club.name),
        node(
          "small",
          "",
          club.attended + " / " + club.registered + " lượt đã điểm danh",
        ),
      );
      row.append(
        node("span", "avatar", initials(club.name)),
        info,
        node(
          "span",
          "badge " + (club.checkin_open ? "" : "neutral"),
          club.checkin_open ? "Đang mở" : "Đang đóng",
        ),
      );
      recent.append(row);
    });
  else
    data.recent.forEach((person) => {
      const row = node("div", "recent-row"),
        info = node("div", "person-info");
      info.append(
        node("strong", "", person.name),
        node("small", "", person.student_id),
      );
      row.append(
        node("span", "avatar", initials(person.name)),
        info,
        node(
          "time",
          "",
          new Date(person.checked_at).toLocaleTimeString("vi-VN", {
            timeZone: "Asia/Ho_Chi_Minh",
            hour: "2-digit",
            minute: "2-digit",
          }),
        ),
        icon("check", "check-icon"),
      );
      recent.append(row);
    });
  if (!recent.childElementCount) {
    const empty = node("div", "empty-activity");
    empty.append(
      icon("store"),
      node(
        "span",
        "",
        state.club
          ? "Những lượt ghé đầu tiên sẽ xuất hiện ở đây."
          : "Thêm gian hàng CLB để bắt đầu ngày hội.",
      ),
    );
    recent.append(empty);
  }
  $("club-board-panel").hidden = !data.club_summaries;
  if (data.club_summaries)
    $("club-board").replaceChildren(
      ...data.club_summaries.map((club) => {
        const button = node("button", "club-tile"),
          heading = node("div"),
          progress = node("progress");
        const title = node("span", "club-tile-title");
        title.append(clubMark(club.name), node("strong", "", club.name));
        heading.append(title, icon("arrow"));
        progress.max = 100;
        progress.value = club.rate;
        progress.setAttribute("aria-label", "Tỷ lệ điểm danh " + club.name);
        button.append(
          heading,
          node(
            "p",
            "",
            club.attended + " đã điểm danh · " + club.pending + " đang chờ",
          ),
          progress,
          node("small", "", number(club.rate) + "%"),
        );
        button.onclick = guarded(async () => {
          $("clubs").value = club.id;
          await selectClub();
        });
        return button;
      }),
    );
}
async function loadMyStatus() {
  if (!state.club) return;
  const epoch = state.epoch,
    data = await api(clubPath() + "/me");
  if (epoch !== state.epoch) return;
  const open = state.event.checkin_open && data.club.checkin_open;
  state.club.checkin_open = data.club.checkin_open;
  state.club.registered = data.registered;
  state.club.attended = data.attended;
  let message = "Đưa mã QR cho admin tại gian hàng " + state.club.name + ".",
    kind = "";
  if (!data.registered) {
    message =
      manager() || superUser()
        ? "Bạn đang quản trị gian hàng. Vé cá nhân dành cho người đã tham gia CLB."
        : "Bạn chưa tham gia " +
          state.club.name +
          ". Bấm Tham gia CLB để nhận vé.";
    kind = "warning";
  } else if (data.attended) {
    message = "Bạn đã điểm danh · " + dateTime(data.checked_at);
    kind = "success";
    clearQr("Đã xác nhận tham gia. Hẹn gặp tại những kết nối tiếp theo!");
  } else if (!open) {
    message =
      "Đã tham gia " +
      state.club.name +
      ". Gian hàng chưa mở điểm danh; mã QR sẽ sẵn sàng khi admin mở.";
    kind = "warning";
    clearQr();
  }
  $("ticket-status").className = "alert " + kind;
  $("ticket-status").textContent = message;
  $("get-qr").disabled = !data.registered || data.attended || !open;
  $("get-qr").hidden = !data.registered || data.attended || !open;
  $("join-club").hidden =
    data.registered || !state.event.checkin_open || !canJoin();
  $("qr").hidden = !data.registered || data.attended || !open;
  $("student-status-title").textContent = data.attended
    ? "Bạn đã để lại dấu ấn!"
    : "Sẵn sàng khám phá?";
  $("student-status-text").textContent = data.attended
    ? "Đã xác nhận tại " +
      state.club.name +
      " lúc " +
      dateTime(data.checked_at) +
      ". Chọn CLB khác để tiếp tục hành trình."
    : message;
}
function canJoin() {
  return (
    !state.studentEmailOnly ||
    /^[0-9]{6,15}@student\.hcmute\.edu\.vn$/.test(state.me?.email || "")
  );
}
function renderStudentCatalog() {
  const registered = state.clubs.filter((club) => club.registered);
  $("catalog-count").textContent = state.clubs.length + " CLB";
  $("my-ticket-shortcut").hidden = !registered.length;
  if (!state.clubs.length) {
    $("student-status-title").textContent = "Sự kiện đã mở";
    $("student-status-text").textContent =
      "Các gian hàng sẽ xuất hiện khi ban tổ chức thêm CLB vào ngày hội.";
    $("student-clubs").replaceChildren(
      node(
        "p",
        "empty-activity",
        "Ban tổ chức đang chuẩn bị các gian hàng. Danh sách CLB sẽ tự cập nhật tại đây.",
      ),
    );
    return;
  }
  if (!state.club) {
    $("student-status-title").textContent = "Ngày hội đang chờ bạn";
    $("student-status-text").textContent = registered.length
      ? "Bạn đã tham gia " +
        registered.length +
        " CLB. Mở vé để xem trạng thái và mã QR của từng gian hàng."
      : "Chọn một gian hàng trong danh sách và bấm Tham gia CLB để nhận vé của mình.";
  }
  $("student-clubs").replaceChildren(
    ...state.clubs.map((club) => {
      const card = node("article", "student-club-card"),
        heading = node("div", "student-club-heading"),
        copy = node("div");
      copy.append(
        node("h3", "", club.name),
        node(
          "span",
          "badge " + (club.registered ? "" : "neutral"),
          club.attended
            ? "Đã điểm danh"
            : club.registered
              ? "Đã tham gia"
              : "Chưa tham gia",
        ),
      );
      heading.append(clubMark(club.name), copy);
      const button = node(
        "button",
        "button " + (club.registered ? "secondary" : ""),
        club.registered ? "Xem vé của tôi" : "Tham gia CLB",
      );
      button.setAttribute(
        "aria-label",
        (club.registered ? "Xem vé " : "Tham gia ") + club.name,
      );
      button.disabled =
        !club.registered && (!state.event.checkin_open || !canJoin());
      button.onclick = guarded(async () => {
        $("clubs").value = club.id;
        await selectClub();
        if (!club.registered) await joinSelectedClub();
        else await showView("ticket");
      });
      card.append(
        heading,
        node(
          "p",
          "",
          club.description ||
            "Kết nối và khám phá hoạt động cùng " + club.name + ".",
        ),
        node(
          "span",
          "club-checkin-note",
          club.checkin_open && state.event.checkin_open
            ? "Đang mở điểm danh"
            : "Chưa mở điểm danh",
        ),
        button,
      );
      return card;
    }),
  );
}
async function joinSelectedClub() {
  const epoch = state.epoch,
    id = state.club.id;
  await api(clubPath() + "/join", { method: "POST" });
  if (epoch !== state.epoch) return;
  await loadEvents({ clubId: id });
  await showView("ticket");
  notice("Đã tham gia " + state.club.name + ". Vé cá nhân đã sẵn sàng.");
}
async function loadSettings() {
  if (!superUser()) return;
  const epoch = state.epoch,
    path = state.club ? clubPath() : null;
  const [admins, superadmins] = await Promise.all([
    path ? api(path + "/admins") : Promise.resolve([]),
    api("/superadmins"),
  ]);
  if (epoch !== state.epoch) return;
  $("admins").replaceChildren();
  if (!path)
    $("admins").append(
      node("p", "hint", "Chọn một CLB ở phía trên để quản lý đội ngũ admin."),
    );
  admins.forEach((person) =>
    renderPerson($("admins"), person, () =>
      api(path + "/admins/" + person.id, { method: "DELETE" }),
    ),
  );
  $("superadmins").replaceChildren();
  superadmins.users.forEach((person) =>
    renderPerson(
      $("superadmins"),
      person,
      superadmins.bootstrap_emails.includes(person.email)
        ? null
        : () => api("/superadmins/" + person.id, { method: "DELETE" }),
    ),
  );
}
function renderPerson(container, person, revoke) {
  const row = node("div", "people-row"),
    info = node("div", "person-info");
  info.append(node("strong", "", person.name), node("small", "", person.email));
  row.append(node("span", "avatar", initials(person.name)), info);
  if (revoke) {
    const button = node("button", "button secondary", "Thu hồi");
    button.onclick = () => {
      $("confirm-message").textContent =
        "Thu hồi quyền của " +
        person.name +
        " (" +
        person.email +
        ")? Thay đổi có hiệu lực ngay.";
      confirmAction = async () => {
        await revoke();
        $("confirm-dialog").close();
        notice("Đã thu hồi quyền.");
        await bootUser();
      };
      openDialog("confirm-dialog");
    };
    row.append(button);
  } else row.append(node("span", "badge neutral", "Khởi tạo"));
  container.append(row);
}
async function selectClub() {
  state.epoch++;
  stopCamera();
  clearQr();
  state.club =
    state.clubs.find((item) => item.id === Number($("clubs").value)) || null;
  state.offset = 0;
  $("filter").reset();
  $("students").replaceChildren();
  $("scan-result").replaceChildren(
    icon("scan"),
    node("span", "", "Chưa có lượt quét nào trong phiên này."),
  );
  $("scan-result").className = "scan-result";
  applyPermissions();
  renderContext();
  await showView(state.view);
}
function clearQr(message = "Mã QR sẽ hiển thị tại đây.") {
  state.qrRun++;
  state.qrWanted = false;
  clearInterval(state.qrTimer);
  $("qr-countdown").hidden = true;
  $("qr").replaceChildren(icon("ticket"), node("p", "", message));
  $("get-qr").textContent = "Hiển thị mã QR";
}
async function generateQr() {
  const epoch = state.epoch,
    run = ++state.qrRun,
    path = clubPath();
  clearInterval(state.qrTimer);
  state.qrWanted = true;
  $("qr").replaceChildren(node("p", "", "Đang tạo mã QR…"));
  try {
    const data = await api(path + "/qr");
    if (
      epoch !== state.epoch ||
      run !== state.qrRun ||
      state.view !== "ticket" ||
      document.hidden
    )
      return;
    const image = node("img");
    image.src = data.image_data_url;
    image.alt = "QR điểm danh cá nhân";
    $("qr").replaceChildren(image);
    $("get-qr").textContent = "Làm mới mã QR";
    $("qr-countdown").hidden = false;
    $("qr-progress").max = data.expires_in;
    const expiresAt = Date.now() + data.expires_in * 1000;
    const tick = () => {
      const left = Math.max(0, Math.ceil((expiresAt - Date.now()) / 1000));
      $("qr-time").textContent = "Tự làm mới sau " + left + " giây";
      $("qr-progress").value = left;
      if (!left) {
        clearInterval(state.qrTimer);
        if (state.qrWanted && !document.hidden && run === state.qrRun)
          generateQr().catch((error) => notice(error.message, true));
      }
    };
    tick();
    state.qrTimer = setInterval(tick, 1000);
  } catch (error) {
    if (epoch === state.epoch && run === state.qrRun)
      clearQr("Chưa tạo được mã. Bấm hiển thị để thử lại.");
    throw error;
  }
}
function stopCamera() {
  state.cameraRun++;
  state.stream?.getTracks().forEach((track) => track.stop());
  state.stream = null;
  $("camera").srcObject = null;
  $("camera").hidden = true;
  $("camera-placeholder").hidden = false;
  $("camera-stop").hidden = true;
  $("camera-start").hidden = false;
  $("camera-state").textContent = "Camera đang tắt";
}
async function loadDecoder() {
  if (window.jsQR) return window.jsQR;
  if (!decoderPromise)
    decoderPromise = new Promise((resolve, reject) => {
      const script = document.createElement("script");
      script.src = "/ui/vendor/jsQR.js";
      script.onload = () => resolve(window.jsQR);
      script.onerror = () => {
        decoderPromise = null;
        script.remove();
        reject(Error("Chưa tải được bộ đọc QR. Kiểm tra kết nối rồi thử lại."));
      };
      document.head.append(script);
    });
  return decoderPromise;
}
async function startCamera() {
  stopCamera();
  if (!state.event.checkin_open || !state.club.checkin_open)
    throw Error("Mở điểm danh sự kiện và gian hàng trước khi quét.");
  if (!navigator.mediaDevices?.getUserMedia)
    throw Error("Thiết bị chưa cho phép camera. Bạn có thể chọn ảnh QR.");
  const run = state.cameraRun,
    epoch = state.epoch;
  let detector;
  try {
    if ("BarcodeDetector" in window)
      detector = new BarcodeDetector({ formats: ["qr_code"] });
  } catch {}
  const decode = detector ? null : await loadDecoder();
  let stream;
  try {
    stream = await navigator.mediaDevices.getUserMedia({
      video: { facingMode: { ideal: "environment" } },
      audio: false,
    });
  } catch {
    throw Error(
      "Chưa mở được camera. Cho phép truy cập trong trình duyệt hoặc chọn ảnh QR.",
    );
  }
  if (
    run !== state.cameraRun ||
    epoch !== state.epoch ||
    state.view !== "checkin" ||
    document.hidden
  ) {
    stream.getTracks().forEach((track) => track.stop());
    return;
  }
  state.stream = stream;
  $("camera").srcObject = stream;
  $("camera").hidden = false;
  $("camera-placeholder").hidden = true;
  $("camera-start").hidden = true;
  $("camera-stop").hidden = false;
  $("camera-state").textContent = "Đang quét · " + state.club.name;
  try {
    await $("camera").play();
  } catch {
    stopCamera();
    throw Error("Chưa phát được camera. Thử bật lại hoặc chọn ảnh QR.");
  }
  const canvas = document.createElement("canvas"),
    context = canvas.getContext("2d", { willReadFrequently: true });
  let lastValue = "",
    lastAt = 0;
  const loop = async () => {
    if (run !== state.cameraRun) return;
    try {
      let value;
      if (detector) value = (await detector.detect($("camera")))[0]?.rawValue;
      else if ($("camera").videoWidth) {
        const scale = Math.min(1, 800 / $("camera").videoWidth);
        canvas.width = Math.floor($("camera").videoWidth * scale);
        canvas.height = Math.floor($("camera").videoHeight * scale);
        context.drawImage($("camera"), 0, 0, canvas.width, canvas.height);
        const pixels = context.getImageData(0, 0, canvas.width, canvas.height);
        value = decode(pixels.data, pixels.width, pixels.height, {
          inversionAttempts: "dontInvert",
        })?.data;
      }
      if (run !== state.cameraRun) return;
      if (
        value &&
        !state.scanBusy &&
        (value !== lastValue || Date.now() - lastAt > 6000)
      ) {
        lastValue = value;
        lastAt = Date.now();
        await submitScan(value);
      }
    } catch (error) {
      if (run === state.cameraRun) notice(error.message, true);
    }
    if (run === state.cameraRun) setTimeout(loop, 300);
  };
  loop();
}
async function submitScan(value) {
  if (state.scanBusy) return;
  const path = clubPath(),
    epoch = state.epoch;
  state.scanBusy = true;
  try {
    const result = await api(path + "/attendance/scan", {
      method: "POST",
      json: { token: value.trim() },
    });
    if (epoch !== state.epoch) return;
    $("scan-result").className = "scan-result success";
    $("scan-result").replaceChildren(
      icon("check"),
      node(
        "strong",
        "",
        result.already_checked_in
          ? "Đã điểm danh trước đó"
          : "Điểm danh thành công",
      ),
      node("span", "", result.name + " · " + result.student_id),
      node("small", "", dateTime(result.checked_at)),
    );
    notice(
      (result.already_checked_in ? "Đã xác nhận trước đó: " : "Chào mừng ") +
        result.name,
    );
  } catch (error) {
    if (epoch === state.epoch) {
      $("scan-result").className = "scan-result error";
      $("scan-result").replaceChildren(
        icon("info"),
        node("span", "", error.message),
      );
    }
    throw error;
  } finally {
    state.scanBusy = false;
  }
}
async function scanFile(file) {
  if (!file) return;
  if (file.size > 15 * 1024 * 1024) throw Error("Chọn ảnh QR nhỏ hơn 15 MB.");
  const epoch = state.epoch,
    decode = await loadDecoder(),
    image = await createImageBitmap(file);
  try {
    const scale = Math.min(1, 1600 / Math.max(image.width, image.height)),
      canvas = document.createElement("canvas");
    canvas.width = Math.floor(image.width * scale);
    canvas.height = Math.floor(image.height * scale);
    const context = canvas.getContext("2d", { willReadFrequently: true });
    context.drawImage(image, 0, 0, canvas.width, canvas.height);
    const pixels = context.getImageData(0, 0, canvas.width, canvas.height),
      result = decode(pixels.data, pixels.width, pixels.height);
    if (!result)
      throw Error(
        "Chưa tìm thấy mã QR trong ảnh. Chọn ảnh rõ, đủ bốn góc của mã.",
      );
    if (epoch === state.epoch) await submitScan(result.data);
  } finally {
    image.close();
    $("qr-file").value = "";
  }
}
async function download(path, name) {
  const blob = await api(path),
    url = URL.createObjectURL(blob),
    link = node("a");
  link.href = url;
  link.download = name;
  document.body.append(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
function openEvent(edit) {
  editingEvent = edit;
  openDialog("event-dialog");
  $("event-dialog-title").textContent = edit
    ? "Chỉnh sửa sự kiện"
    : "Tạo sự kiện";
  if (edit) {
    for (const key of ["title", "description", "image_url"])
      $("event-form").elements[key].value = state.event[key] || "";
    $("event-form").elements.starts_at.value = new Date(
      new Date(state.event.starts_at).getTime() + 7 * 3600000,
    )
      .toISOString()
      .slice(0, 16);
  }
}
function openPerson(action) {
  personAction = action;
  openDialog("person-dialog");
  $("person-dialog-title").textContent = {
    student: "Thêm người tham gia",
    admin: "Thêm admin CLB",
    superadmin: "Cấp quyền superadmin",
    access: "Cấp quyền theo email",
  }[action];
  $("person-context").textContent =
    action === "access"
      ? "Nhập email Google rồi chọn vai trò. Admin chỉ có quyền tại CLB được gán."
      : action === "superadmin"
        ? "Quyền này cho phép quản lý toàn bộ sự kiện và tất cả CLB."
        : "Thêm vào gian hàng " +
          state.club.name +
          ". Có thể thêm trước lần đăng nhập đầu tiên.";
  const form = $("person-form"),
    unified = action === "access";
  form.elements.name.required = action === "student";
  $("person-name-help").hidden = action === "student";
  $("grant-role-field").hidden = !unified;
  form.elements.role.disabled = !unified;
  form.elements.club_id.replaceChildren(
    new Option("Chọn CLB trong sự kiện hiện tại…", ""),
    ...state.clubs.map((club) => new Option(club.name, club.id)),
  );
  if (state.club) form.elements.club_id.value = state.club.id;
  updateGrantScope();
}
function updateGrantScope() {
  const form = $("person-form"),
    scoped = personAction === "access" && form.elements.role.value === "admin";
  $("grant-club-field").hidden = !scoped;
  form.elements.club_id.disabled = !scoped;
}
all("[data-nav]").forEach(
  (button) => (button.onclick = guarded(() => showView(button.dataset.nav))),
);
all("[data-go]").forEach(
  (button) => (button.onclick = guarded(() => showView(button.dataset.go))),
);
all("[data-close]").forEach(
  (button) => (button.onclick = () => button.closest("dialog").close()),
);
all("dialog").forEach((dialog) =>
  dialog.addEventListener("click", (event) => {
    if (event.target !== dialog) return;
    const rect = dialog.getBoundingClientRect();
    if (
      event.clientX < rect.left ||
      event.clientX > rect.right ||
      event.clientY < rect.top ||
      event.clientY > rect.bottom
    )
      dialog.close();
  }),
);
$("notice-close").onclick = () => ($("notice").hidden = true);
$("logout").onclick = logout;
document.addEventListener("click", (event) => {
  const menu = $("account-menu");
  if (!menu.contains(event.target)) menu.open = false;
});
document.addEventListener("keydown", (event) => {
  if (event.key === "Escape" && $("account-menu").open) {
    $("account-menu").open = false;
    $("account-menu").querySelector("summary").focus();
  }
});
$("reload").onclick = guarded(() => bootUser());
$("events").onchange = guarded(() =>
  loadEvents({ eventId: Number($("events").value) }),
);
$("clubs").onchange = guarded(selectClub);
$("get-qr").onclick = guarded(generateQr);
$("join-club").onclick = guarded(joinSelectedClub);
$("camera-start").onclick = guarded(startCamera);
$("camera-stop").onclick = stopCamera;
$("qr-file").onchange = guarded((event) => scanFile(event.target.files[0]));
$("filter").onsubmit = guarded(async () => {
  state.offset = 0;
  await loadStudents();
});
$("prev").onclick = guarded(async () => {
  state.offset = Math.max(0, state.offset - 25);
  await loadStudents();
});
$("next").onclick = guarded(async () => {
  if (state.offset + 25 < state.total) {
    state.offset += 25;
    await loadStudents();
  }
});
$("export").onclick = guarded(() =>
  download(
    clubPath() + "/attendance/export?" + filterQuery(),
    "attendance-" + state.club.id + ".xlsx",
  ),
);
$("template").onclick = guarded(() =>
  download(clubPath() + "/students/template", "club-students-template.xlsx"),
);
$("new-event").onclick = () => openEvent(false);
$("edit-event").onclick = () => openEvent(true);
for (const id of ["new-club", "settings-new-club"])
  $(id).onclick = () => openDialog("club-dialog");
$("empty-action").onclick = () =>
  state.event ? openDialog("club-dialog") : openEvent(false);
$("add-student").onclick = () => openPerson("student");
$("add-admin").onclick = () => openPerson("admin");
$("grant-super").onclick = () => openPerson("superadmin");
$("grant-access").onclick = () => openPerson("access");
$("person-form").elements.role.onchange = updateGrantScope;
$("open-import").onclick = () => {
  $("import-context").textContent =
    "Danh sách chỉ được thêm vào " + state.club.name + ".";
  $("import-result").hidden = true;
  openDialog("import-dialog");
};
$("toggle-club").onclick = guarded(async () => {
  const result = await api(clubPath() + "/checkin", {
    method: "PATCH",
    json: { checkin_open: !state.club.checkin_open },
  });
  state.club.checkin_open = result.checkin_open;
  renderContext();
  notice(
    result.checkin_open
      ? "Đã mở điểm danh gian hàng."
      : "Đã tạm đóng điểm danh gian hàng.",
  );
  if (!result.checkin_open) stopCamera();
});
$("toggle-event").onclick = guarded(async () => {
  const { title, description, image_url, starts_at } = state.event;
  await api(eventPath(), {
    method: "PUT",
    json: {
      title,
      description,
      image_url,
      starts_at,
      checkin_open: !state.event.checkin_open,
    },
  });
  await loadEvents();
  notice("Đã cập nhật trạng thái sự kiện.");
});
bindForm("event-form", async (data) => {
  const payload = {
    title: data.get("title").trim(),
    description: data.get("description"),
    image_url: data.get("image_url") || null,
    starts_at: data.get("starts_at") + ":00+07:00",
    checkin_open: editingEvent ? state.event.checkin_open : false,
  };
  const result = await api(editingEvent ? eventPath() : "/events", {
    method: editingEvent ? "PUT" : "POST",
    json: payload,
  });
  $("event-dialog").close();
  await loadEvents({ eventId: result.id });
  notice("Đã lưu sự kiện.");
});
bindForm("club-form", async (data) => {
  const result = await api(eventPath() + "/clubs", {
    method: "POST",
    json: {
      name: data.get("name").trim(),
      description: data.get("description"),
      checkin_open: false,
    },
  });
  $("club-dialog").close();
  await loadEvents({ clubId: result.id });
  await showView("settings");
  notice("Đã tạo gian hàng. Bạn có thể thêm admin cho CLB.");
});
bindForm("person-form", async (data) => {
  const payload = {
    name: data.get("name").trim(),
    email: data.get("email").trim(),
  };
  if (personAction === "student")
    await api(clubPath() + "/students", { method: "POST", json: payload });
  else {
    payload.role = personAction === "access" ? data.get("role") : personAction;
    if (payload.role === "admin") {
      if (!state.event)
        throw Error("Tạo hoặc chọn sự kiện trước khi gán admin CLB.");
      payload.event_id = state.event.id;
      payload.club_id =
        personAction === "access"
          ? Number(data.get("club_id"))
          : state.club?.id;
      if (!payload.club_id)
        throw Error("Chọn CLB được quản lý trước khi cấp quyền.");
    }
    await api("/access/grants", { method: "POST", json: payload });
  }
  $("person-dialog").close();
  await showView(state.view);
  notice("Đã thêm tài khoản.");
});
bindForm("import", async (data) => {
  if (data.get("file").size > 5 * 1024 * 1024)
    throw Error("File tối đa 5 MB. Hãy chia danh sách thành các tệp nhỏ hơn.");
  const result = await api(clubPath() + "/students/import", {
    method: "POST",
    body: data,
  });
  const output = $("import-result");
  output.hidden = false;
  output.replaceChildren(
    node(
      "strong",
      "",
      result.errors.length
        ? "Chưa nhập dòng nào. Sửa các dòng sau rồi tải lại."
        : "Đã thêm " + result.imported + " người tham gia.",
    ),
  );
  if (result.duplicates.length)
    output.append(
      node("p", "", result.duplicates.length + " dòng trùng được bỏ qua."),
    );
  const list = node("ul");
  [
    ...result.errors.map((item) => "Dòng " + item.row + ": " + item.error),
    ...result.duplicates.map((item) => "Dòng " + item.row + ": " + item.reason),
  ].forEach((message) => list.append(node("li", "", message)));
  output.append(list);
  await loadStudents();
});
bindForm("confirm-form", async () => {
  if (confirmAction) await confirmAction();
});
$("scan").onsubmit = guarded(async (event) => {
  await submitScan(new FormData(event.target).get("token"));
  event.target.reset();
});
function onlineStatus() {
  $("offline").hidden = navigator.onLine;
}
window.addEventListener("online", onlineStatus);
window.addEventListener("offline", onlineStatus);
onlineStatus();
window.addEventListener("pagehide", () => {
  stopCamera();
  clearQr();
});
document.addEventListener("visibilitychange", () => {
  if (document.hidden) {
    stopCamera();
    clearQr("Mã đã được tạm ẩn. Bấm hiển thị để tiếp tục.");
  }
});
let refreshing = false;
setInterval(async () => {
  if (
    !state.me ||
    document.hidden ||
    refreshing ||
    document.querySelector("dialog[open]")
  )
    return;
  refreshing = true;
  const epoch = state.epoch;
  try {
    const identity = await api("/auth/me");
    if (epoch !== state.epoch) return;
    const events = await workspaceEvents();
    if (epoch !== state.epoch) return;
    if (!state.event) {
      if (events.length) await loadEvents();
      return;
    }
    const clubs = await workspaceClubs();
    if (epoch !== state.epoch) return;
    if (
      identity.role !== state.me.role ||
      JSON.stringify(identity.admin_club_ids) !==
        JSON.stringify(state.me.admin_club_ids) ||
      !events.some((item) => item.id === state.event.id) ||
      (state.club && !clubs.some((item) => item.id === state.club.id))
    ) {
      await bootUser();
      return;
    }
    if (
      events.map((item) => item.id).join() !==
        state.events.map((item) => item.id).join() ||
      clubs.map((item) => item.id).join() !==
        state.clubs.map((item) => item.id).join()
    ) {
      await loadEvents();
      return;
    }
    state.me = identity;
    state.clubs = clubs;
    state.event = events.find((item) => item.id === state.event.id);
    if (state.club)
      state.club = clubs.find((item) => item.id === state.club.id);
    if (!state.event.checkin_open || (state.club && !state.club.checkin_open))
      stopCamera();
    renderContext();
    if (state.view === "overview" && (manager() || superUser()))
      await loadSummary();
    else if (state.view === "participants" && manager()) await loadStudents();
    else if (state.club && ["ticket", "overview"].includes(state.view))
      await loadMyStatus();
  } catch (error) {
    if (epoch === state.epoch) notice(error.message, true);
  } finally {
    refreshing = false;
  }
}, 10000);
(async () => {
  try {
    const config = await api("/auth/config");
    state.studentEmailOnly = config.student_email_only;
    $("policy").textContent = config.student_email_only
      ? "Sinh viên dùng @student.hcmute.edu.vn. Admin có thể dùng email Google đã được cấp quyền."
      : "Dùng tài khoản Google có email đã xác minh.";
    // Restore a session even when Google Sign-In is temporarily unavailable.
    if (state.token) await bootUser();
    if (!config.client_id) {
      $("login-note").textContent =
        "Đăng nhập chưa được cấu hình. Liên hệ ban tổ chức để được hỗ trợ.";
      return;
    }
    let tries = 0;
    const init = () => {
      if (!window.google?.accounts?.id) {
        if (++tries < 40) setTimeout(init, 250);
        else
          $("login-note").textContent =
            "Chưa tải được Google Sign-In. Kiểm tra mạng hoặc tải lại trang.";
        return;
      }
      google.accounts.id.initialize({
        client_id: config.client_id,
        callback: guarded(async (response) => {
          const data = await api("/auth/google", {
            method: "POST",
            json: { credential: response.credential },
          });
          state.token = data.access_token;
          sessionStorage.setItem("fit-token", state.token);
          await bootUser();
        }),
      });
      google.accounts.id.renderButton($("google-button"), {
        theme: "outline",
        size: "large",
        text: "signin_with",
        shape: "rectangular",
        width: 300,
      });
    };
    init();
  } catch (error) {
    notice(error.message, true);
  }
})();
