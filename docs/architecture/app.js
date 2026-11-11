const traces = {
  g0: {
    prompt: "xin chào",
    actor: "CLI · chưa có session/auth trong G0",
    actorNote: "G0 hiện chưa có session/auth",
    steps: [
      ["CLI", "`lrh ask` tạo một user Message. `--system` nếu có sẽ tạo thêm system Message."],
      ["REQUEST", "GenerateRequest nhận messages, temperature=0 và max_output_tokens=1024."],
      ["CACHE", "Response cache tra theo model/cache_tag và nội dung GenerateRequest; cache hit kết thúc tại đây."],
      ["LIMIT", "Cache miss đi qua throttle và SpendGuard trước khi gọi provider."],
      ["ADAPTER", "GeminiModel ánh xạ system messages sang config.system_instruction; user messages sang contents."],
      ["API", "Gemma 4 31B nhận system instruction, contents và config thinking HIGH; trả GenerateResult." ]
    ],
    result: "Đây là đường đang có trong code. Chưa có auth, RAG retrieval, intent routing hoặc MCP trong request này."
  },
  order: {
    prompt: "Đơn AB123 của tôi đang ở đâu rồi?",
    actor: "customer · c001 (mục tiêu thiết kế; identity lấy từ session)",
    actorNote: "actor lấy từ session, không từ prompt",
    steps: [
      ["AUTH", "Session hợp lệ tạo actor_context: role=customer, customer_id=c001."],
      ["INTENT", "Parser lấy order_id=AB123; intent ứng viên là order_status."],
      ["QUERY", "Code tạo truy vấn theo order_id và owner_customer_id=c001 từ actor_context."],
      ["ACL", "Nếu bản ghi thuộc c001, chỉ bản ghi đó đi vào authorized_evidence."],
      ["PROMPT", "Builder đưa câu hỏi và evidence có nguồn vào contents; hướng dẫn phù hợp vào system instruction."],
      ["MODEL", "Gemini adapter gửi GenerateRequest đã ghép tới model API."]
    ],
    result: "Đây là luồng mục tiêu sau khi có retrieval và quyền. Dữ liệu đơn không vào prompt trước khi qua điều kiện owner."
  },
  cross: {
    prompt: "Cho tôi xem hóa đơn của đơn c002-1002 nhé.",
    actor: "customer · c001 (mục tiêu thiết kế)",
    actorNote: "actor lấy từ session, không từ prompt",
    steps: [
      ["AUTH", "Actor vẫn là c001/customer; giá trị c002 trong câu hỏi không đổi session."],
      ["INTENT", "Request được hiểu là tra hóa đơn; ID chỉ là tham số cần tra."],
      ["QUERY", "Truy vấn luôn scope owner_customer_id=c001, do code gắn vào."],
      ["ACL", "Hóa đơn của c002 không khớp scope nên nội dung không được lấy."],
      ["POLICY", "Trả lớp NOT_FOUND đã quy định; không đưa nội dung bị chặn vào prompt."],
      ["MODEL", "Đường deny có thể trả phản hồi cố định mà không cần gọi model."]
    ],
    result: "Sơ đồ này mô tả yêu cầu của DATA-CONTRACT; chưa phải hành vi đã triển khai trong repo."
  },
  ambiguous: {
    prompt: "Tôi không muốn hủy đơn AB123, chỉ muốn biết tình trạng.",
    actor: "customer · c001 (mục tiêu thiết kế)",
    actorNote: "actor lấy từ session, không từ prompt",
    steps: [
      ["AUTH", "Actor context lấy từ session."],
      ["PARSE", "Trích order_id=AB123 và phát hiện câu có phủ định quanh ý định hủy."],
      ["ROUTE", "Không route sang cancel; câu nêu rõ muốn xem tình trạng nên chọn order_status."],
      ["SCOPE", "Dùng owner_customer_id=c001 trong truy vấn dù embedding có thể thấy từ ‘hủy’."],
      ["PROMPT", "Chọn hướng dẫn trạng thái đơn, không mở tool ghi/xóa."],
      ["MODEL", "Model chỉ trả lời từ record đã qua quyền."]
    ],
    result: "Nếu câu chỉ nói ‘không muốn hủy’ mà không nói muốn làm gì, route cần hỏi lại thay vì đoán intent."
  }
};

const $ = (selector, root = document) => root.querySelector(selector);
const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];

function setView(view) {
  $$(".view-tab").forEach((button) => {
    const active = button.dataset.view === view;
    button.classList.toggle("is-active", active);
    button.setAttribute("aria-selected", String(active));
  });
  $$(".view-panel").forEach((panel) => {
    const active = panel.id === `${view}-view`;
    panel.classList.toggle("is-active", active);
    panel.hidden = !active;
  });
}

function renderTrace(name) {
  const trace = traces[name];
  if (!trace) return;
  $$(".trace-button").forEach((button) => {
    const active = button.dataset.trace === name;
    button.classList.toggle("is-active", active);
    button.setAttribute("aria-pressed", String(active));
  });
  $("#trace-prompt").textContent = `“${trace.prompt}”`;
  $("#trace-actor").textContent = trace.actor;
  $("#trace-actor").nextElementSibling.textContent = trace.actorNote;
  $("#trace-steps").innerHTML = trace.steps.map(([label, copy], index) => `
    <article class="trace-step"><span class="trace-step-num">${String(index + 1).padStart(2, "0")}</span><div><span class="trace-type">${label}</span><b>${label === "API" || label === "MODEL" ? "Model boundary" : label === "ACL" || label === "SCOPE" ? "Access boundary" : label}</b><p>${copy}</p></div></article>
  `).join("");
  $("#trace-result").innerHTML = `<strong>TRACE RESULT</strong>${trace.result}`;
}

$$ (".view-tab").forEach((button) => button.addEventListener("click", () => setView(button.dataset.view)));
$$ (".trace-button").forEach((button) => button.addEventListener("click", () => renderTrace(button.dataset.trace)));

renderTrace("g0");
