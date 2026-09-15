(function () {
frappe.pages["sales-cockpit"].on_page_load = function (wrapper) {
  const page = frappe.ui.make_app_page({
    parent: wrapper,
    title: __("Sales Cockpit"),
    single_column: true,
  });

  const state = {
    page,
    wrapper,
    period: "quarter",
    data: null,
    loading: false,
    realtimeBound: false,
  };
  wrapper.northstarState = state;
  buildShell(state);
  bindActions(state);
  refreshCockpit(state);
};

frappe.pages["sales-cockpit"].on_page_show = function (wrapper) {
  const state = wrapper.northstarState;
  if (state && !state.loading) refreshCockpit(state);
};

function buildShell(state) {
  state.page.set_primary_action(__("Add Lead"), () => showLeadDialog(state), "add");
  state.page.add_menu_item(__("Organizations"), () => frappe.set_route("List", "CRM Organization"));
  state.page.add_menu_item(__("Document Register"), () => frappe.set_route("List", "CRM Document Asset"));
  state.page.add_menu_item(__("Forecast History"), () => frappe.set_route("List", "CRM Forecast Snapshot"));

  $(state.page.body).html(`
    <div class="northstar-cockpit">
      <section class="ns-hero">
        <div>
          <p class="ns-eyebrow">LIVE SALES OPERATIONS</p>
          <h2>${__("Customer relationships, from first signal to signed business.")}</h2>
          <p>${__("A unified view of pipeline, follow-up, commercial value, consent, and customer evidence.")}</p>
        </div>
        <label class="ns-period">${__("Period")}
          <select data-action="period">
            <option value="quarter">${__("This quarter")}</option>
            <option value="month">${__("This month")}</option>
          </select>
        </label>
      </section>

      <section class="ns-metrics" data-region="metrics">
        ${metricSkeletons()}
      </section>

      <section class="ns-main-grid">
        <article class="ns-panel ns-pipeline-panel">
          <header class="ns-panel-header">
            <div><span>${__("Revenue engine")}</span><h3>${__("Opportunity pipeline")}</h3></div>
            <button class="btn btn-default btn-sm" data-action="open-opportunities">${__("All opportunities")}</button>
          </header>
          <div class="ns-kanban" data-region="pipeline">${boardSkeletons()}</div>
        </article>

        <aside class="ns-side-stack">
          <article class="ns-panel ns-activity-panel">
            <header class="ns-panel-header">
              <div><span>${__("Action queue")}</span><h3>${__("Next activities")}</h3></div>
              <button class="ns-icon-button" data-action="add-activity" title="${__("Add activity")}">+</button>
            </header>
            <div data-region="activities">${listSkeletons()}</div>
          </article>

          <article class="ns-panel ns-data-panel">
            <header class="ns-panel-header"><div><span>${__("Information architecture")}</span><h3>${__("Data landscape")}</h3></div></header>
            <button class="ns-data-row" data-action="open-structured">
              <i class="ns-data-icon structured">DB</i><span><strong>${__("Structured")}</strong><small>${__("Customers, leads, deals, quotes, consent")}</small></span><em>${__("DocTypes")}</em>
            </button>
            <button class="ns-data-row" data-action="open-integrations">
              <i class="ns-data-icon semi">{ }</i><span><strong>${__("Semi-structured")}</strong><small>${__("API events, score traces, extracted metadata")}</small></span><em>${__("JSON")}</em>
            </button>
            <button class="ns-data-row" data-action="open-documents">
              <i class="ns-data-icon unstructured">TXT</i><span><strong>${__("Unstructured")}</strong><small>${__("Emails, notes, proposals, transcripts, files")}</small></span><em>${__("Content")}</em>
            </button>
          </article>
        </aside>
      </section>
    </div>
  `);
}

function bindActions(state) {
  const root = $(state.page.body);
  root.on("change", '[data-action="period"]', (event) => {
    state.period = event.target.value;
    refreshCockpit(state);
  });
  root.on("click", '[data-action="open-opportunities"]', () => frappe.set_route("List", "CRM Opportunity"));
  root.on("click", '[data-action="open-structured"]', () => frappe.set_route("List", "CRM Organization"));
  root.on("click", '[data-action="open-integrations"]', () => frappe.set_route("List", "CRM Integration Event"));
  root.on("click", '[data-action="open-documents"]', () => frappe.set_route("List", "CRM Document Asset"));
  root.on("click", '[data-action="add-activity"]', () => frappe.new_doc("CRM Activity"));
  root.on("click", ".ns-deal-card", (event) => {
    if ($(event.target).closest("select").length) return;
    frappe.set_route("Form", "CRM Opportunity", event.currentTarget.dataset.name);
  });
  root.on("change", ".ns-stage-select", async (event) => {
    event.stopPropagation();
    const select = event.currentTarget;
    select.disabled = true;
    try {
      const targetStage = (state.data.stages || []).find((stage) => stage.name === select.value);
      const lossReason = toInteger(targetStage?.is_lost) ? await requestLossReason() : null;
      if (toInteger(targetStage?.is_lost) && !lossReason) {
        select.value = select.dataset.stage;
        return;
      }
      await frappe.call({
        method: "northstar_crm.api.move_opportunity",
        type: "POST",
        args: {
          opportunity_name: select.dataset.name,
          pipeline_stage: select.value,
          loss_reason: lossReason,
        },
        freeze: true,
      });
      frappe.show_alert({ message: __("Pipeline updated"), indicator: "green" });
      await refreshCockpit(state);
    } finally {
      select.disabled = false;
    }
  });

  if (!state.realtimeBound && frappe.realtime) {
    frappe.realtime.on("northstar_crm_pipeline_update", () => refreshCockpit(state));
    state.realtimeBound = true;
  }
}

async function refreshCockpit(state) {
  if (state.loading) return;
  state.loading = true;
  $(state.page.body).find(".northstar-cockpit").addClass("is-loading");
  try {
    const response = await frappe.call({
      method: "northstar_crm.api.get_sales_cockpit",
      type: "GET",
      args: { period: state.period },
    });
    state.data = response.message || {};
    renderMetrics(state);
    renderPipeline(state);
    renderActivities(state);
  } catch (error) {
    $(state.page.body).find('[data-region="pipeline"]').html(emptyState(__("Pipeline unavailable"), __("Refresh the page or check your permissions.")));
    throw error;
  } finally {
    state.loading = false;
    $(state.page.body).find(".northstar-cockpit").removeClass("is-loading");
  }
}

function renderMetrics(state) {
  const forecast = state.data.forecast || {};
  const opportunities = state.data.opportunities || [];
  const stale = opportunities.filter((row) => toInteger(row.is_stale)).length;
  const metrics = [
    { label: __("Pipeline value"), value: money(forecast.pipeline_amount, state.data.currency), note: __("Open value in period"), tone: "lime" },
    { label: __("Weighted forecast"), value: money(forecast.weighted_forecast, state.data.currency), note: __("Probability adjusted"), tone: "blue" },
    { label: __("Active opportunities"), value: String(forecast.total_count || 0), note: __("Closing in selected period"), tone: "purple" },
    { label: __("Needs attention"), value: String(stale + (state.data.overdue_count || 0)), note: `${stale} ${__("stale")}, ${state.data.overdue_count || 0} ${__("overdue")}`, tone: "orange" },
  ];
  $(state.page.body).find('[data-region="metrics"]').html(metrics.map((item) => `
    <article class="ns-metric ${item.tone}">
      <span>${escapeHtml(item.label)}</span><strong>${escapeHtml(item.value)}</strong><small>${escapeHtml(item.note)}</small>
      <i></i>
    </article>
  `).join(""));
}

function renderPipeline(state) {
  const opportunities = state.data.opportunities || [];
  const configuredStages = state.data.stages || [];
  const activeStageNames = configuredStages
    .filter((stage) => !toInteger(stage.is_won) && !toInteger(stage.is_lost))
    .map((stage) => stage.name);
  const opportunityStageNames = opportunities.map((row) => row.pipeline_stage).filter(Boolean);
  const knownStages = [...new Set([...activeStageNames, ...opportunityStageNames])];
  if (!knownStages.length) {
    $(state.page.body).find('[data-region="pipeline"]').html(emptyState(__("No opportunities yet"), __("Add a lead and convert it to start the pipeline.")));
    return;
  }
  const movableStages = configuredStages.length ? configuredStages.map((stage) => stage.name) : knownStages;
  const stageOptions = movableStages.map((stage) => `<option value="${escapeHtml(stage)}">${escapeHtml(stage)}</option>`).join("");
  const html = knownStages.map((stage) => {
    const rows = opportunities.filter((row) => row.pipeline_stage === stage);
    const amount = rows.reduce((sum, row) => sum + toNumber(row.amount), 0);
    return `
      <section class="ns-stage-column">
        <header><div><i></i><strong>${escapeHtml(stage)}</strong><span>${rows.length}</span></div><em>${money(amount)}</em></header>
        <div class="ns-stage-list">
          ${rows.length ? rows.map((row) => dealCard(row, stageOptions, state.data.currency)).join("") : `<p class="ns-stage-empty">${__("No deals in this stage")}</p>`}
        </div>
      </section>
    `;
  }).join("");
  $(state.page.body).find('[data-region="pipeline"]').html(html);
  $(state.page.body).find(".ns-stage-select").each((_, select) => { select.value = select.dataset.stage; });
}

function dealCard(row, stageOptions, currency) {
  return `
    <article class="ns-deal-card${toInteger(row.is_stale) ? " is-stale" : ""}" data-name="${escapeHtml(row.name)}">
      <div class="ns-deal-top"><span>${escapeHtml(initials(row.organization))}</span><strong>${money(row.amount, row.currency || currency)}</strong></div>
      <h4>${escapeHtml(row.opportunity_name)}</h4>
      <p>${escapeHtml(row.organization || __("No organization"))}</p>
      <footer>
        <small>${row.expected_close_date ? frappe.datetime.str_to_user(row.expected_close_date) : __("No close date")}</small>
        <select class="ns-stage-select" data-name="${escapeHtml(row.name)}" data-stage="${escapeHtml(row.pipeline_stage)}" aria-label="${__("Move opportunity stage")}">${stageOptions}</select>
      </footer>
    </article>
  `;
}

function renderActivities(state) {
  const activities = state.data.activities || [];
  const html = activities.length ? activities.slice(0, 7).map((item) => `
    <button class="ns-activity" data-doctype="CRM Activity" data-name="${escapeHtml(item.name)}">
      <i class="${escapeHtml((item.activity_type || "task").toLowerCase().replaceAll(" ", "-"))}">${escapeHtml((item.activity_type || "T").slice(0, 1))}</i>
      <span><strong>${escapeHtml(item.subject)}</strong><small>${escapeHtml(item.activity_type)} · ${frappe.datetime.prettyDate(item.activity_datetime)}</small></span>
      <em class="${item.priority === "Urgent" || item.priority === "High" ? "high" : ""}">${escapeHtml(item.priority || "Medium")}</em>
    </button>
  `).join("") : emptyState(__("Nothing due"), __("Your activity queue is clear."));
  const region = $(state.page.body).find('[data-region="activities"]');
  region.html(html);
  region.find(".ns-activity").on("click", (event) => frappe.set_route("Form", event.currentTarget.dataset.doctype, event.currentTarget.dataset.name));
}

function showLeadDialog(state) {
  const dialog = new frappe.ui.Dialog({
    title: __("Add Lead"),
    fields: [
      { fieldname: "lead_name", fieldtype: "Data", label: __("Contact name"), reqd: 1 },
      { fieldname: "organization_name", fieldtype: "Data", label: __("Organization") },
      { fieldname: "email", fieldtype: "Data", options: "Email", label: __("Email") },
      { fieldname: "mobile_no", fieldtype: "Data", options: "Phone", label: __("Mobile") },
      { fieldname: "estimated_value", fieldtype: "Currency", label: __("Estimated value") },
      { fieldname: "business_need", fieldtype: "Small Text", label: __("Business need") },
    ],
    primary_action_label: __("Create Lead"),
    async primary_action(values) {
      await frappe.call({ method: "northstar_crm.api.create_lead", type: "POST", args: { data: values }, freeze: true });
      dialog.hide();
      frappe.show_alert({ message: __("Lead created"), indicator: "green" });
      refreshCockpit(state);
    },
  });
  dialog.show();
}

function requestLossReason() {
  return new Promise((resolve) => {
    let completed = false;
    const dialog = new frappe.ui.Dialog({
      title: __("Close Opportunity as Lost"),
      fields: [
        { fieldname: "loss_reason", fieldtype: "Small Text", label: __("Loss reason"), reqd: 1 },
      ],
      primary_action_label: __("Close as Lost"),
      primary_action(values) {
        completed = true;
        dialog.hide();
        resolve(values.loss_reason);
      },
    });
    dialog.$wrapper.on("hidden.bs.modal", () => {
      if (!completed) resolve(null);
    });
    dialog.show();
  });
}

function metricSkeletons() {
  return Array.from({ length: 4 }, () => '<div class="ns-skeleton ns-metric-skeleton"></div>').join("");
}

function boardSkeletons() {
  return Array.from({ length: 4 }, () => '<div class="ns-skeleton ns-column-skeleton"></div>').join("");
}

function listSkeletons() {
  return Array.from({ length: 4 }, () => '<div class="ns-skeleton ns-list-skeleton"></div>').join("");
}

function emptyState(title, detail) {
  return `<div class="ns-empty"><strong>${escapeHtml(title)}</strong><span>${escapeHtml(detail)}</span></div>`;
}

function money(value, currency = "SAR") {
  return new Intl.NumberFormat(undefined, { style: "currency", currency: currency || "SAR", maximumFractionDigits: 0 }).format(toNumber(value));
}

function toNumber(value) {
  const number = Number.parseFloat(value);
  return Number.isFinite(number) ? number : 0;
}

function toInteger(value) {
  const number = Number.parseInt(value, 10);
  return Number.isFinite(number) ? number : 0;
}

function initials(value) {
  return String(value || "NA").split(/\s+/).slice(0, 2).map((part) => part[0]).join("").toUpperCase();
}

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>'"]/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;" }[char]));
}
})();
