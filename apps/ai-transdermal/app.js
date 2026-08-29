(function () {
  "use strict";

  const form = document.getElementById("moleculeForm");
  const input = document.getElementById("moleculeInput");
  const message = document.getElementById("searchMessage");
  const resultSection = document.getElementById("fentanyl");
  const chartBlock = document.getElementById("chartBlock");
  const chart = document.getElementById("fentanylChart");
  const chartGrid = document.getElementById("chartGrid");
  const chartLoading = document.getElementById("chartLoading");
  const chartError = document.getElementById("chartError");
  const retryChart = document.getElementById("retryChart");
  const modelPath = document.getElementById("modelPath");
  const humanPath = document.getElementById("humanPath");
  const humanPoints = document.getElementById("humanPoints");
  const removalLine = document.getElementById("removalLine");
  const timeCursor = document.getElementById("timeCursor");
  const modelCursor = document.getElementById("modelCursor");
  const humanCursor = document.getElementById("humanCursor");
  const timeReadout = document.getElementById("timeReadout");
  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)");

  const plot = { left: 82, right: 1088, top: 30, bottom: 354 };
  const domain = { xMax: 144, yMax: 1 };
  let modelSeries = [];
  let humanSeries = [];
  let chartReady = false;
  let chartAnimated = false;
  let animationFrame = 0;

  function normalize(value) {
    return String(value || "")
      .toLocaleLowerCase()
      .replace(/[\s_\-/()（）µμ]+/g, "")
      .trim();
  }

  function isFentanylQuery(value) {
    const term = normalize(value);
    return ["芬太尼", "fentanyl", "25ug/h", "25ugh", "fentanyltransdermalsystem"]
      .some(function (alias) { return normalize(alias).includes(term) || term.includes(normalize(alias)); });
  }

  form.addEventListener("submit", function (event) {
    event.preventDefault();
    if (!input.value.trim()) {
      message.textContent = "请输入芬太尼或 Fentanyl。";
      input.focus();
      return;
    }
    if (!isFentanylQuery(input.value)) {
      message.textContent = "当前仅开放芬太尼结果，其他药物正在接入。";
      return;
    }
    message.textContent = "已匹配芬太尼。";
    resultSection.scrollIntoView({ behavior: reduceMotion.matches ? "auto" : "smooth", block: "start" });
  });

  function parseCsv(text) {
    const lines = text.trim().split(/\r?\n/);
    const headers = lines.shift().split(",");
    return lines.map(function (line) {
      const values = line.split(",");
      return headers.reduce(function (row, header, index) {
        row[header] = values[index];
        return row;
      }, {});
    });
  }

  function xScale(value) {
    return plot.left + (value / domain.xMax) * (plot.right - plot.left);
  }

  function yScale(value) {
    return plot.bottom - (value / domain.yMax) * (plot.bottom - plot.top);
  }

  function makeSvgElement(tag, attributes, text) {
    const element = document.createElementNS("http://www.w3.org/2000/svg", tag);
    Object.keys(attributes).forEach(function (key) { element.setAttribute(key, attributes[key]); });
    if (text) element.textContent = text;
    return element;
  }

  function buildGrid() {
    chartGrid.replaceChildren();
    [0, 24, 48, 72, 96, 120, 144].forEach(function (tick) {
      const x = xScale(tick);
      chartGrid.appendChild(makeSvgElement("line", { x1: x, x2: x, y1: plot.top, y2: plot.bottom, class: "grid-line" }));
      chartGrid.appendChild(makeSvgElement("text", { x: x, y: plot.bottom + 27, class: "axis-label", "text-anchor": "middle" }, String(tick)));
    });
    [0, .2, .4, .6, .8, 1].forEach(function (tick) {
      const y = yScale(tick);
      chartGrid.appendChild(makeSvgElement("line", { x1: plot.left, x2: plot.right, y1: y, y2: y, class: "grid-line" }));
      chartGrid.appendChild(makeSvgElement("text", { x: plot.left - 16, y: y + 4, class: "axis-label", "text-anchor": "end" }, tick.toFixed(1)));
    });
    chartGrid.appendChild(makeSvgElement("line", { x1: plot.left, x2: plot.right, y1: plot.bottom, y2: plot.bottom, class: "axis-line" }));
    chartGrid.appendChild(makeSvgElement("line", { x1: plot.left, x2: plot.left, y1: plot.top, y2: plot.bottom, class: "axis-line" }));
    chartGrid.appendChild(makeSvgElement("text", { x: (plot.left + plot.right) / 2, y: 410, class: "axis-title", "text-anchor": "middle" }, "贴剂应用后时间（小时）"));
    chartGrid.appendChild(makeSvgElement("text", { x: 22, y: 192, class: "axis-title", "text-anchor": "middle", transform: "rotate(-90 22 192)" }, "血浆浓度（ng/mL）"));
    const removalX = xScale(72);
    removalLine.setAttribute("x1", removalX);
    removalLine.setAttribute("x2", removalX);
    removalLine.setAttribute("y1", plot.top);
    removalLine.setAttribute("y2", plot.bottom);
    chartGrid.appendChild(makeSvgElement("text", { x: removalX + 8, y: plot.top + 15, class: "removal-label" }, "72 h 揭贴"));
  }

  function pathFromSeries(series) {
    return series.map(function (point, index) {
      return `${index === 0 ? "M" : "L"}${xScale(point.time).toFixed(2)} ${yScale(point.value).toFixed(2)}`;
    }).join(" ");
  }

  function valueAtTime(series, time) {
    if (!series.length) return 0;
    if (time <= series[0].time) return series[0].value;
    if (time >= series[series.length - 1].time) return series[series.length - 1].value;
    let low = 0;
    let high = series.length - 1;
    while (high - low > 1) {
      const middle = Math.floor((low + high) / 2);
      if (series[middle].time <= time) low = middle;
      else high = middle;
    }
    const start = series[low];
    const end = series[high];
    const ratio = (time - start.time) / (end.time - start.time);
    return start.value + (end.value - start.value) * ratio;
  }

  function positionCursor(circle, series, time) {
    circle.setAttribute("cx", xScale(time));
    circle.setAttribute("cy", yScale(valueAtTime(series, time)));
  }

  function showFinalChart() {
    [modelPath, humanPath].forEach(function (path) {
      path.style.strokeDasharray = "none";
      path.style.strokeDashoffset = "0";
    });
    const finalTime = domain.xMax;
    timeCursor.setAttribute("x1", xScale(finalTime));
    timeCursor.setAttribute("x2", xScale(finalTime));
    positionCursor(modelCursor, modelSeries, finalTime);
    positionCursor(humanCursor, humanSeries, finalTime);
    timeReadout.textContent = `${finalTime} h`;
  }

  function animateChart() {
    if (!chartReady || chartAnimated) return;
    chartAnimated = true;
    if (reduceMotion.matches) {
      showFinalChart();
      return;
    }
    const modelLength = modelPath.getTotalLength();
    const humanLength = humanPath.getTotalLength();
    modelPath.style.strokeDasharray = String(modelLength);
    modelPath.style.strokeDashoffset = String(modelLength);
    humanPath.style.strokeDasharray = String(humanLength);
    humanPath.style.strokeDashoffset = String(humanLength);
    modelPath.animate([{ strokeDashoffset: modelLength }, { strokeDashoffset: 0 }], {
      duration: 3200, easing: "cubic-bezier(.16, 1, .3, 1)", fill: "forwards"
    });
    humanPath.animate([{ strokeDashoffset: humanLength }, { strokeDashoffset: 0 }], {
      duration: 3200, easing: "cubic-bezier(.16, 1, .3, 1)", fill: "forwards"
    });
    const startedAt = performance.now();
    function update(now) {
      const progress = Math.min((now - startedAt) / 3200, 1);
      const eased = 1 - Math.pow(1 - progress, 4);
      const time = domain.xMax * eased;
      const x = xScale(time);
      timeCursor.setAttribute("x1", x);
      timeCursor.setAttribute("x2", x);
      positionCursor(modelCursor, modelSeries, time);
      positionCursor(humanCursor, humanSeries, time);
      timeReadout.textContent = `${Math.round(time)} h`;
      if (progress < 1) animationFrame = window.requestAnimationFrame(update);
      else showFinalChart();
    }
    animationFrame = window.requestAnimationFrame(update);
  }

  function renderChart(rows) {
    modelSeries = rows
      .filter(function (row) { return row.molecule === "fentanyl" && row.series === "osp_marketed_regimen_prediction"; })
      .map(function (row) { return { time: Number(row.time_h), value: Number(row.concentration) }; })
      .filter(function (point) { return Number.isFinite(point.time) && Number.isFinite(point.value) && point.time <= domain.xMax; })
      .sort(function (a, b) { return a.time - b.time; });
    humanSeries = rows
      .filter(function (row) { return row.molecule === "fentanyl" && row.series === "published_human_approx_digitized"; })
      .map(function (row) { return { time: Number(row.time_h), value: Number(row.concentration) }; })
      .filter(function (point) { return Number.isFinite(point.time) && Number.isFinite(point.value) && point.time <= domain.xMax; })
      .sort(function (a, b) { return a.time - b.time; });
    if (modelSeries.length < 2 || humanSeries.length < 2) throw new Error("Fentanyl series missing");
    buildGrid();
    modelPath.setAttribute("d", pathFromSeries(modelSeries));
    humanPath.setAttribute("d", pathFromSeries(humanSeries));
    humanPoints.replaceChildren();
    humanSeries.forEach(function (point) {
      humanPoints.appendChild(makeSvgElement("circle", { cx: xScale(point.time), cy: yScale(point.value), r: 4, class: "human-point" }));
    });
    timeCursor.setAttribute("y1", plot.top);
    timeCursor.setAttribute("y2", plot.bottom);
    positionCursor(modelCursor, modelSeries, 0);
    positionCursor(humanCursor, humanSeries, 0);
    chartLoading.hidden = true;
    chartError.hidden = true;
    chart.removeAttribute("hidden");
    chartReady = true;
  }

  async function loadChart() {
    chartReady = false;
    chartAnimated = false;
    window.cancelAnimationFrame(animationFrame);
    chart.setAttribute("hidden", "");
    chartError.hidden = true;
    chartLoading.hidden = false;
    try {
      const response = await fetch("data/raw/fentanyl_curves.csv?v=20260814-4", { cache: "no-store" });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      renderChart(parseCsv(await response.text()));
    } catch (error) {
      chartLoading.hidden = true;
      chartError.hidden = false;
      console.error("Unable to load fentanyl curve data", error);
    }
  }

  const observer = new IntersectionObserver(function (entries) {
    if (entries.some(function (entry) { return entry.isIntersecting; })) animateChart();
  }, { threshold: .28 });

  observer.observe(chartBlock);
  retryChart.addEventListener("click", loadChart);
  window.addEventListener("pagehide", function () {
    observer.disconnect();
    window.cancelAnimationFrame(animationFrame);
  }, { once: true });
  loadChart();
}());
