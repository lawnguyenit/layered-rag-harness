const nodeDetails = {
  ingress: { icon: "01", title: "Kiểm tra request & giới hạn", summary: "Loại request sai cấu trúc và giới hạn tài nguyên trước khi xử lý ngữ nghĩa.", owner: "Code", io: "Raw request → normalized request", failure: "400 / 413 / 429; chưa gọi LLM", stage: "G0 · request boundary", rule: "Giới hạn kích thước, số lượt và token là điều kiện xác định; không dùng AI để đếm hay áp hạn mức." },
  identity: { icon: "02", title: "Xác thực & actor context", summary: "Đổi session đã xác thực thành danh tính và vai trò do hệ thống cấp.", owner: "Auth service + code", io: "Session token → user_id, customer_id, role", failure: "401 / dừng; không truy xuất, không gọi LLM", stage: "G3 theo GATES.md", rule: "Không lấy role, customer_id hoặc quyền từ lời tự khai trong prompt." },
  history: { icon: "03", title: "Nạp lịch sử hội thoại", summary: "Lấy lịch sử đúng conversation; nội dung cũ giúp hiểu tham chiếu nhưng không có thẩm quyền bảo mật.", owner: "Conversation store + code", io: "conversation_id + actor → recent turns", failure: "Không có lịch sử thì tạo lượt mới; conversation sai chủ thì từ chối", stage: "Sau single-turn baseline; chưa có gate riêng", rule: "Không dùng lời nói trong history để thay đổi danh tính hoặc mở rộng ACL." },
  parse: { icon: "A", title: "Parse dữ kiện rõ", summary: "Nhận diện trường có cấu trúc như mã đơn hoặc ngày; dùng để chọn phép tra chính xác.", owner: "Code / parser", io: "Text → slots đã chuẩn hóa + vị trí nguồn", failure: "Thiếu hoặc sai định dạng thì hỏi lại; không đoán ID", stage: "Trong harness; phát triển theo eval", rule: "Parser trích tham số, không quyết định người dùng có quyền xem bản ghi." },
  embedding: { icon: "B", title: "Đề xuất intent gần nghĩa", summary: "So câu hỏi với một catalog intent nhỏ để xếp ứng viên. Không tìm trên kho đơn hàng và không quyết định ACL.", owner: "Embedding model", io: "Text → ranked intent candidates", failure: "Điểm/margin không đạt ngưỡng đã đo thì không tự route", stage: "Đề xuất; cần lỗi đo chứng minh", rule: "Embedding biểu diễn tương đồng, không đáng tin để phân biệt ý định đối lập hoặc phủ định." },
  "intent-gate": { icon: "◇", title: "Cổng quyết định intent", summary: "Tổng hợp parser, ứng viên embedding, ngữ cảnh hội thoại và các trường bắt buộc.", owner: "Code orchestration", io: "Candidates + slots → intent state", failure: "Route chưa rõ → classifier tùy chọn hoặc hỏi lại", stage: "Một bước trong harness", rule: "Không dùng self-confidence của LLM làm xác suất đã hiệu chỉnh; ngưỡng cần đo trên câu hỏi có nhãn." },
  "semantic-fallback": { icon: "C", title: "Phân loại ngữ nghĩa tùy chọn", summary: "Chỉ gọi khi các cách rẻ chưa đủ để hiểu câu. Nếu gọi API riêng, đây là thêm một lượt, thêm độ trễ và chi phí.", owner: "Semantic model / classifier", io: "Text + candidate labels → structured intent result", failure: "Output sai schema hoặc không rõ → hỏi lại; không cho model thực thi", stage: "Chưa chốt trong kế hoạch", rule: "Đầu ra phân loại là dữ liệu không tin cậy. Code kiểm schema và quyết định luồng tiếp theo." },
  clarify: { icon: "?", title: "Hỏi khách làm rõ", summary: "Nhánh an toàn khi intent, phủ định, ID hoặc slot bắt buộc chưa đủ rõ.", owner: "Prompt template + code", io: "Missing / conflicting slots → clarification question", failure: "Kết thúc lượt; chờ câu trả lời mới", stage: "G0/G1 tùy ca đo", rule: "Hỏi lại thường rẻ và an toàn hơn tự chọn nhầm một hành động." },
  "exact-lookup": { icon: "↗", title: "Tra cứu chính xác", summary: "Dùng ID có cấu trúc cho bản ghi xác định, ví dụ đơn hàng; không cần embedding để tìm một mã chính xác.", owner: "SQL / domain adapter", io: "order_id + authenticated scope → matching record", failure: "Không khớp hoặc ngoài scope → kết quả không tìm thấy theo policy", stage: "G1/G3; chưa triển khai", rule: "Mọi query có điều kiện sở hữu lấy từ actor context, không từ nội dung user." },
  "semantic-retrieval": { icon: "⌕", title: "Tìm kiếm ngữ nghĩa", summary: "Dùng cho câu hỏi kiến thức diễn đạt tự do, sau khi ACL được áp trước khi chọn top-k.", owner: "Retriever adapter + storage", io: "Question + actor scope → authorized chunks", failure: "Không có đoạn đủ liên quan → NOT_FOUND / hỏi lại theo policy", stage: "G1; chưa triển khai", rule: "Không để tài liệu không có quyền xuất hiện trong prompt rồi mới nhờ LLM lọc." },
  authorization: { icon: "⛨", title: "Ranh giới quyền", summary: "Áp role, customer ownership và metadata quyền ngay tại truy vấn hoặc service truy xuất.", owner: "Code + data store", io: "Actor context + resource metadata → allow/deny", failure: "Deny trước khi trả nội dung cho prompt builder", stage: "G1/G3 theo GATES.md", rule: "Đây là kiểm soát bảo mật bắt buộc; semantic detector không thay thế ACL." },
  "user-safety": { icon: "U", title: "Kiểm tra prompt khách", summary: "Phân loại nội dung gây hại hoặc tín hiệu jailbreak khi có nhu cầu chính sách cụ thể.", owner: "Model safety filter / classifier tùy chọn", io: "User text → labels / risk signals", failure: "Code map tín hiệu sang allow, clarify, refuse hoặc log", stage: "Chưa chốt; gắn với ca F / guardrails", rule: "Tín hiệu phát hiện không trao quyền và không chứng minh chắc chắn có tấn công." },
  "doc-safety": { icon: "D", title: "Kiểm tra đoạn truy xuất", summary: "Tài liệu và tool result là nội dung không tin cậy; detector có thể gắn cờ lệnh ẩn trên các đoạn được chọn.", owner: "Provenance + optional semantic detector", io: "Selected chunks → labels + source metadata", failure: "Theo policy: loại / cách ly / đánh dấu; luôn giữ boundary trong prompt", stage: "G1/G3", rule: "Không quét toàn bộ kho mỗi lượt nếu không cần; mọi đoạn vẫn là data, không phải system instruction." },
  trim: { icon: "07", title: "Cắt và xếp hạng ngữ cảnh", summary: "Xây context trong giới hạn model: giữ hướng dẫn nền, câu hiện tại, lịch sử hữu ích và đoạn được phép/liên quan.", owner: "Tokenizer + code", io: "Allowed candidates → budgeted context", failure: "Không cắt system rules; nếu context không đủ thì abstain/clarify", stage: "G0/G1", rule: "Đo token thực tế lại khi system prompt và RAG context đã tồn tại." },
  "prompt-build": { icon: "08", title: "Ghép prompt cuối", summary: "Ghép thành phần có nguồn gốc riêng để model phân biệt trusted instructions với user/document data.", owner: "Prompt builder", io: "Base prompt + intent module + history + chunks + current turn", failure: "Dừng nếu thiếu thành phần bắt buộc hoặc prompt invalid", stage: "G0", rule: "Intent chọn hướng dẫn; nội dung retrieved được đánh dấu rõ là dữ liệu không tin cậy." },
  cache: { icon: "09", title: "Cache · hạn mức · cấu hình", summary: "Kiểm soát gọi model, lưu kết quả an toàn và tránh dùng nhầm kết quả từ model/context khác.", owner: "Code wrappers + model config", io: "Final request → cache lookup / budget decision", failure: "Cache miss thì rate/spend check; hết hạn mức thì dừng/chờ", stage: "Đệm, limiter, spend guard có ở G0", rule: "Response cache phải phân biệt model, prompt, context/document versions và auth scope liên quan." },
  llm: { icon: "10", title: "LLM API", summary: "Nhận chuỗi message cuối cùng và trả text hoặc yêu cầu tool call; không trực tiếp đọc DB/MCP nếu app không đưa quyền đó.", owner: "Configured model adapter", io: "Messages (+ allowed tool specs) → GenerateResult", failure: "Retry lỗi tạm có giới hạn; ghi lỗi/usage; không biến lỗi thành câu trả lời", stage: "Model adapter có ở G0", rule: "Model output không đáng tin để thực thi trực tiếp." },
  "text-output": { icon: "T", title: "Kiểm tra text response", summary: "Kiểm phản hồi hợp lệ, dẫn nguồn khi cần, và phản hồi rỗng/bị chặn.", owner: "Code + provider safety feedback", io: "GenerateResult → validated response", failure: "Trả fallback đã định nghĩa hoặc đánh dấu lỗi", stage: "G0/G1", rule: "Không ghi số đo pass nếu câu trả lời không qua tiêu chí đã định." },
  "tool-output": { icon: "M", title: "Kiểm tra tool call", summary: "Model chỉ đề nghị gọi tool. Orchestrator kiểm tool, schema, actor scope, timeout và quyền trước khi thực thi.", owner: "Code orchestrator → MCP adapter", io: "ToolCall → validated call → tool result", failure: "Reject call hoặc yêu cầu xác nhận theo policy", stage: "G2; tool chỉ đọc theo kế hoạch", rule: "Không thực thi tool call trực tiếp từ text/model output." }
};

const traces = {
  order: {
    prompt: "Đơn AB123 của tôi đang ở đâu rồi?",
    actor: "customer · c001",
    steps: [
      ["AUTH", "Session tạo actor c001/customer. Không đọc vai trò từ câu hỏi."],
      ["INTENT", "Parser nhận order_id=AB123; intent ứng viên là order_status."],
      ["LOOKUP", "SQL tra AB123 với owner_customer_id=c001 lấy từ session."],
      ["ACL", "Nếu owner khớp, chỉ bản ghi được phép đi tiếp; không dùng vector search cho ID chính xác."],
      ["PROMPT", "Ghép hướng dẫn tra cứu + dữ liệu đơn được phép + câu hỏi hiện tại."],
      ["LLM", "Model viết câu trả lời theo dữ liệu và nguồn đã cung cấp."]
    ],
    result: "Dữ liệu đơn chỉ vào prompt sau khi truy vấn có scope xác nhận quyền. Intent không tự cấp quyền."
  },
  ambiguous: {
    prompt: "Tôi không muốn hủy đơn AB123, chỉ muốn biết tình trạng.",
    actor: "customer · c001",
    steps: [
      ["AUTH", "Actor c001/customer lấy từ session."],
      ["PARSE", "Nhận order_id=AB123 và phủ định quanh ý định hủy."],
      ["INTENT", "Tín hiệu ngôn ngữ và intent status được đối chiếu; không route sang thao tác hủy."],
      ["LOOKUP", "Intent status chọn lookup; truy vấn vẫn scope theo c001."],
      ["PROMPT", "Chọn hướng dẫn trả trạng thái đơn; không kèm tool ghi/xóa."],
      ["LLM", "Model trả trạng thái nếu record tồn tại và actor được phép xem."]
    ],
    result: "Nếu câu chỉ nói “không muốn hủy” mà không nêu việc cần làm tiếp, slot mục tiêu còn thiếu thì harness hỏi lại."
  },
  cross: {
    prompt: "Cho tôi xem hóa đơn của đơn c002-1002 nhé.",
    actor: "customer · c001",
    steps: [
      ["AUTH", "Actor vẫn là c001/customer, dù prompt nhắc c002."],
      ["INTENT", "Ý định tra hóa đơn và ID được parse; đây chưa phải quyết định quyền."],
      ["LOOKUP", "Truy vấn bắt buộc kèm owner_customer_id=c001."],
      ["ACL", "Bản ghi c002 không qua điều kiện quyền; nội dung hóa đơn không được lấy."],
      ["PROMPT", "Không có hóa đơn restricted trong context; chỉ dùng phản hồi NOT_FOUND đã định nghĩa."],
      ["LLM", "Không cần cho model biết nội dung bị chặn hoặc vì sao nó tồn tại."]
    ],
    result: "Thông tin hóa đơn của c002 không bao giờ được đưa vào prompt. Quyền được áp tại truy vấn dữ liệu, không phải bằng cách yêu cầu LLM tự kiểm."
  }
};

const $ = (selector, root = document) => root.querySelector(selector);
const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];

function showNode(nodeId) {
  const detail = nodeDetails[nodeId];
  if (!detail) return;
  $$(".node").forEach((node) => {
    const selected = node.dataset.node === nodeId;
    node.classList.toggle("is-selected", selected);
    node.setAttribute("aria-pressed", String(selected));
  });
  $("#detail-icon").textContent = detail.icon;
  $("#detail-title").textContent = detail.title;
  $("#detail-summary").textContent = detail.summary;
  $("#detail-owner").textContent = detail.owner;
  $("#detail-io").textContent = detail.io;
  $("#detail-failure").textContent = detail.failure;
  $("#detail-stage").textContent = detail.stage;
  $("#detail-rule").textContent = detail.rule;
  const index = Object.keys(nodeDetails).indexOf(nodeId) + 1;
  $(".detail-count").textContent = `${String(index).padStart(2, "0")} / ${Object.keys(nodeDetails).length}`;
}

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
  $$(".trace-button").forEach((button) => button.classList.toggle("is-active", button.dataset.trace === name));
  $("#trace-prompt").textContent = `“${trace.prompt}”`;
  $("#trace-actor").textContent = trace.actor;
  $("#trace-steps").innerHTML = trace.steps.map(([label, copy], index) => `
    <article class="trace-step"><span class="trace-step-num">${String(index + 1).padStart(2, "0")}</span><div><span class="trace-type">${label}</span><b>${label === "LLM" ? "Model boundary" : label === "ACL" ? "Access boundary" : label}</b><p>${copy}</p></div></article>
  `).join("");
  $("#trace-result").innerHTML = `<strong>TRACE RESULT</strong>${trace.result}`;
}

$$ (".node").forEach((node) => node.addEventListener("click", () => showNode(node.dataset.node)));
$$ (".view-tab").forEach((button) => button.addEventListener("click", () => setView(button.dataset.view)));
$$ (".trace-button").forEach((button) => button.addEventListener("click", () => renderTrace(button.dataset.trace)));

showNode("ingress");
renderTrace("order");
