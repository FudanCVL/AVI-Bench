(function () {
  "use strict";

  var SVG_NS = "http://www.w3.org/2000/svg";
  var DAY_MS = 24 * 60 * 60 * 1000;
  var PROVIDER_STYLES = {
    google: { color: "#4285f4", shape: "circle" },
    qwen: { color: "#7c3aed", shape: "square" },
    openai: { color: "#11856b", shape: "triangle" }
  };
  var EXTRA_COLORS = ["#d04a35", "#167d9a", "#b17a00", "#bd4d8c", "#566b2f"];
  var EXTRA_SHAPES = ["diamond", "circle", "square", "triangle"];
  var chartPoints = [];
  var providerStyles = {};
  var resizeObserver = null;
  var fallbackResizeBound = false;
  var hideTimer = null;
  var lastWidth = 0;

  function byId(id) {
    return document.getElementById(id);
  }

  function svgElement(tag, attributes, text) {
    var element = document.createElementNS(SVG_NS, tag);
    Object.keys(attributes || {}).forEach(function (name) {
      element.setAttribute(name, attributes[name]);
    });
    if (text !== undefined) {
      element.textContent = text;
    }
    return element;
  }

  function readScore(entry) {
    var taxonomy = entry.scores && entry.scores.taxonomy;
    return taxonomy && taxonomy.l4_domain;
  }

  function collectPoints(data) {
    return data.entries
      .filter(function (entry) {
        var releaseDate = entry.model_release_date;
        var timestamp = Date.parse(releaseDate + "T00:00:00Z");
        var score = readScore(entry);
        return entry.benchmark_version === data.chart_benchmark_version &&
          typeof releaseDate === "string" &&
          /^\d{4}-\d{2}-\d{2}$/.test(releaseDate) &&
          Number.isFinite(timestamp) &&
          typeof score === "number" && Number.isFinite(score) &&
          score >= 0 && score <= 100;
      })
      .map(function (entry) {
        return {
          entry: entry,
          timestamp: Date.parse(entry.model_release_date + "T00:00:00Z"),
          score: readScore(entry),
          provider: String(entry.provider || "Unknown provider")
        };
      })
      .sort(function (left, right) {
        return left.timestamp - right.timestamp ||
          left.entry.model_name.localeCompare(right.entry.model_name, undefined, {
            numeric: true,
            sensitivity: "base"
          }) ||
          left.entry.id.localeCompare(right.entry.id);
      });
  }

  function buildProviderStyles(points) {
    var providers = Array.from(new Set(points.map(function (point) {
      return point.provider;
    }))).sort(function (left, right) {
      return left.localeCompare(right, undefined, { sensitivity: "base" });
    });
    var styles = {};
    var extraIndex = 0;

    providers.forEach(function (provider) {
      var key = provider.trim().toLowerCase();
      styles[provider] = PROVIDER_STYLES[key] || {
        color: EXTRA_COLORS[extraIndex % EXTRA_COLORS.length],
        shape: EXTRA_SHAPES[extraIndex % EXTRA_SHAPES.length]
      };
      if (!PROVIDER_STYLES[key]) {
        extraIndex += 1;
      }
    });
    return styles;
  }

  function addMarker(parent, shape, x, y, size, color, className) {
    var common = { fill: color, class: className || "trend-marker" };
    var marker;
    if (shape === "square") {
      common.x = x - size;
      common.y = y - size;
      common.width = size * 2;
      common.height = size * 2;
      marker = svgElement("rect", common);
    } else if (shape === "triangle") {
      common.d = "M " + x + " " + (y - size - 1) +
        " L " + (x + size + 1) + " " + (y + size) +
        " L " + (x - size - 1) + " " + (y + size) + " Z";
      marker = svgElement("path", common);
    } else if (shape === "diamond") {
      common.d = "M " + x + " " + (y - size - 1) +
        " L " + (x + size + 1) + " " + y +
        " L " + x + " " + (y + size + 1) +
        " L " + (x - size - 1) + " " + y + " Z";
      marker = svgElement("path", common);
    } else {
      common.cx = x;
      common.cy = y;
      common.r = size;
      marker = svgElement("circle", common);
    }
    marker.setAttribute("stroke", "#ffffff");
    marker.setAttribute("stroke-width", "2");
    parent.appendChild(marker);
    return marker;
  }

  function addText(parent, x, y, text, className, attributes) {
    var settings = Object.assign({ x: x, y: y, class: className }, attributes || {});
    var label = svgElement("text", settings, text);
    parent.appendChild(label);
    return label;
  }

  function monthLabel(timestamp) {
    var options = { month: "short", year: "numeric", timeZone: "UTC" };
    return new Intl.DateTimeFormat("en", options).format(new Date(timestamp));
  }

  function dayLabel(timestamp, includeYear) {
    var options = {
      day: "numeric",
      month: "short",
      timeZone: "UTC"
    };
    if (includeYear) {
      options.year = "numeric";
    }
    return new Intl.DateTimeFormat("en", options).format(new Date(timestamp));
  }

  function yearLabel(timestamp) {
    return new Intl.DateTimeFormat("en", {
      year: "numeric",
      timeZone: "UTC"
    }).format(new Date(timestamp));
  }

  function chooseTicks(domainStart, domainEnd, plotWidth) {
    var span = domainEnd - domainStart;
    var maxTicks = Math.max(2, Math.floor(plotWidth / 105));
    var ticks = [];

    if (span <= 45 * DAY_MS) {
      var daySteps = [1, 3, 7, 14];
      var chosenDays = daySteps[daySteps.length - 1];
      daySteps.some(function (step) {
        if (span / (step * DAY_MS) <= maxTicks) {
          chosenDays = step;
          return true;
        }
        return false;
      });
      var firstDay = Math.ceil(domainStart / (chosenDays * DAY_MS)) * chosenDays * DAY_MS;
      var includeYear = new Date(domainStart).getUTCFullYear() !==
        new Date(domainEnd).getUTCFullYear();
      for (var day = firstDay; day <= domainEnd; day += chosenDays * DAY_MS) {
        ticks.push({ timestamp: day, label: dayLabel(day, includeYear) });
      }
      return ticks;
    }

    var startDate = new Date(domainStart);
    var endDate = new Date(domainEnd);
    var spanMonths = (endDate.getUTCFullYear() - startDate.getUTCFullYear()) * 12 +
      endDate.getUTCMonth() - startDate.getUTCMonth() + 1;
    var monthSteps = [1, 2, 4, 6, 12, 24, 60, 120];
    var chosenMonths = monthSteps[monthSteps.length - 1];
    monthSteps.some(function (step) {
      if (spanMonths / step <= maxTicks) {
        chosenMonths = step;
        return true;
      }
      return false;
    });

    var firstMonthIndex = startDate.getUTCFullYear() * 12 + startDate.getUTCMonth();
    var monthIndex = Math.ceil(firstMonthIndex / chosenMonths) * chosenMonths;
    var lastMonthIndex = endDate.getUTCFullYear() * 12 + endDate.getUTCMonth();
    for (; monthIndex <= lastMonthIndex; monthIndex += chosenMonths) {
      var tickDate = new Date(Date.UTC(Math.floor(monthIndex / 12), monthIndex % 12, 1));
      var label = chosenMonths >= 12 && tickDate.getUTCMonth() === 0
        ? yearLabel(tickDate.getTime())
        : monthLabel(tickDate.getTime());
      ticks.push({ timestamp: tickDate.getTime(), label: label });
    }
    return ticks;
  }

  function addLegend() {
    var legend = byId("avi-index-chart-legend");
    legend.replaceChildren();
    Object.keys(providerStyles).forEach(function (provider) {
      var item = document.createElement("span");
      item.className = "trend-legend-item";
      var symbol = document.createElementNS(SVG_NS, "svg");
      symbol.setAttribute("viewBox", "0 0 16 16");
      symbol.setAttribute("aria-hidden", "true");
      addMarker(symbol, providerStyles[provider].shape, 8, 8, 5, providerStyles[provider].color, "trend-legend-marker");
      item.appendChild(symbol);
      var label = document.createElement("span");
      label.textContent = provider;
      item.appendChild(label);
      legend.appendChild(item);
    });
  }

  function showTooltip(point, marker) {
    window.clearTimeout(hideTimer);
    var tooltip = byId("avi-index-chart-tooltip");
    tooltip.replaceChildren();

    var title = document.createElement("strong");
    title.textContent = point.entry.model_name;
    tooltip.appendChild(title);

    var details = document.createElement("dl");
    [
      ["Provider", point.provider],
      ["Released", point.entry.model_release_date],
      ["AVI-Index", point.score.toFixed(2)]
    ].forEach(function (item) {
      var row = document.createElement("div");
      var term = document.createElement("dt");
      term.textContent = item[0];
      var value = document.createElement("dd");
      value.textContent = item[1];
      row.appendChild(term);
      row.appendChild(value);
      details.appendChild(row);
    });
    tooltip.appendChild(details);

    [
      ["Release source", point.entry.model_release_source_url],
      ["Score source", point.entry.source && point.entry.source.url]
    ].forEach(function (item) {
      if (!item[1]) {
        return;
      }
      var link = document.createElement("a");
      link.href = item[1];
      link.target = "_blank";
      link.rel = "noopener noreferrer";
      link.textContent = item[0];
      tooltip.appendChild(link);
    });

    tooltip.hidden = false;
    var markerRect = marker.getBoundingClientRect();
    var plotRect = byId("avi-index-chart-plot").getBoundingClientRect();
    var tooltipWidth = tooltip.offsetWidth;
    var tooltipHeight = tooltip.offsetHeight;
    var left = markerRect.left - plotRect.left + markerRect.width / 2 - tooltipWidth / 2;
    var top = markerRect.top - plotRect.top - tooltipHeight - 10;
    left = Math.max(4, Math.min(left, plotRect.width - tooltipWidth - 4));
    if (top < 4) {
      top = markerRect.bottom - plotRect.top + 10;
    }
    tooltip.style.left = left + "px";
    tooltip.style.top = top + "px";
  }

  function scheduleTooltipHide() {
    window.clearTimeout(hideTimer);
    hideTimer = window.setTimeout(function () {
      byId("avi-index-chart-tooltip").hidden = true;
    }, 140);
  }

  function addPoint(svg, point, x, y, index) {
    var style = providerStyles[point.provider];
    var group = svgElement("g", {
      class: "trend-point",
      tabindex: "0",
      role: "button",
      "aria-describedby": "avi-index-chart-tooltip",
      "aria-label": point.entry.model_name + ", " + point.provider +
        ", released " + point.entry.model_release_date +
        ", AVI-Index " + point.score.toFixed(2),
      "data-entry-id": point.entry.id || String(index)
    });
    group.appendChild(svgElement("circle", {
      class: "trend-point-hit-area",
      cx: x,
      cy: y,
      r: 12
    }));
    addMarker(group, style.shape, x, y, 6, style.color, "trend-point-marker");
    group.addEventListener("pointerenter", function () { showTooltip(point, group); });
    group.addEventListener("pointerleave", scheduleTooltipHide);
    group.addEventListener("focus", function () { showTooltip(point, group); });
    group.addEventListener("blur", scheduleTooltipHide);
    group.addEventListener("click", function () { showTooltip(point, group); });
    group.addEventListener("keydown", function (event) {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        showTooltip(point, group);
      } else if (event.key === "Escape") {
        byId("avi-index-chart-tooltip").hidden = true;
      }
    });
    svg.appendChild(group);
  }

  function drawChart() {
    if (!chartPoints.length) {
      return;
    }
    var svg = byId("avi-index-chart");
    var plot = byId("avi-index-chart-plot");
    var focusedId = document.activeElement && document.activeElement.getAttribute("data-entry-id");
    var width = Math.max(280, Math.round(plot.clientWidth || 960));
    var height = width < 560 ? 310 : 360;
    var margin = { top: 18, right: 18, bottom: 60, left: 55 };
    var plotWidth = width - margin.left - margin.right;
    var plotHeight = height - margin.top - margin.bottom;
    var times = chartPoints.map(function (point) { return point.timestamp; });
    var minTime = Math.min.apply(null, times);
    var maxTime = Math.max.apply(null, times);
    var range = maxTime - minTime;
    var padding = range === 0 ? 30 * DAY_MS : Math.max(DAY_MS, range * 0.035);
    var domainStart = minTime - padding;
    var domainEnd = maxTime + padding;
    var title = svg.querySelector("title");
    var description = svg.querySelector("desc");

    svg.setAttribute("viewBox", "0 0 " + width + " " + height);
    svg.style.height = height + "px";
    svg.replaceChildren(title, description);

    function xFor(timestamp) {
      return margin.left + ((timestamp - domainStart) / (domainEnd - domainStart)) * plotWidth;
    }
    function yFor(score) {
      return margin.top + ((100 - score) / 100) * plotHeight;
    }

    var grid = svgElement("g", { class: "trend-grid" });
    for (var score = 0; score <= 100; score += 20) {
      var y = yFor(score);
      grid.appendChild(svgElement("line", {
        class: "trend-grid-line",
        x1: margin.left,
        x2: width - margin.right,
        y1: y,
        y2: y
      }));
      addText(grid, margin.left - 10, y + 4, String(score), "trend-axis-tick", {
        "text-anchor": "end"
      });
    }
    svg.appendChild(grid);

    var axes = svgElement("g", { class: "trend-axes" });
    axes.appendChild(svgElement("line", {
      class: "trend-axis-line",
      x1: margin.left,
      x2: margin.left,
      y1: margin.top,
      y2: height - margin.bottom
    }));
    axes.appendChild(svgElement("line", {
      class: "trend-axis-line",
      x1: margin.left,
      x2: width - margin.right,
      y1: height - margin.bottom,
      y2: height - margin.bottom
    }));

    chooseTicks(domainStart, domainEnd, plotWidth).forEach(function (tick) {
      var x = xFor(tick.timestamp);
      axes.appendChild(svgElement("line", {
        class: "trend-axis-tick-line",
        x1: x,
        x2: x,
        y1: height - margin.bottom,
        y2: height - margin.bottom + 5
      }));
      addText(axes, x, height - margin.bottom + 22, tick.label, "trend-axis-tick", {
        "text-anchor": "middle"
      });
    });
    addText(axes, margin.left + plotWidth / 2, height - 8, "Model release date", "trend-axis-label", {
      "text-anchor": "middle"
    });
    axes.appendChild(svgElement("text", {
      class: "trend-axis-label",
      transform: "translate(14 " + (margin.top + plotHeight / 2) + ") rotate(-90)",
      "text-anchor": "middle"
    }, "AVI-Index"));
    svg.appendChild(axes);

    if (chartPoints.length > 1) {
      var path = chartPoints.map(function (point, index) {
        return (index === 0 ? "M " : "L ") +
          xFor(point.timestamp).toFixed(2) + " " + yFor(point.score).toFixed(2);
      }).join(" ");
      svg.appendChild(svgElement("path", {
        class: "trend-line",
        d: path
      }));
    }

    chartPoints.forEach(function (point, index) {
      addPoint(svg, point, xFor(point.timestamp), yFor(point.score), index);
    });

    if (focusedId) {
      Array.prototype.find.call(svg.querySelectorAll("[data-entry-id]"), function (point) {
        if (point.getAttribute("data-entry-id") === focusedId) {
          point.focus();
          return true;
        }
        return false;
      });
    }
    lastWidth = width;
  }

  function installResizeObserver() {
    if (resizeObserver || fallbackResizeBound) {
      return;
    }
    var plot = byId("avi-index-chart-plot");
    if ("ResizeObserver" in window) {
      resizeObserver = new ResizeObserver(function () {
        var width = Math.round(plot.clientWidth || 0);
        if (width && Math.abs(width - lastWidth) > 2) {
          drawChart();
        }
      });
      resizeObserver.observe(plot);
    } else {
      fallbackResizeBound = true;
      window.addEventListener("resize", drawChart);
    }
  }

  function render(data) {
    chartPoints = collectPoints(data);
    if (!chartPoints.length) {
      byId("avi-index-chart-content").hidden = true;
      var noDataStatus = byId("avi-index-chart-status");
      noDataStatus.hidden = false;
      noDataStatus.textContent = "No AVI-Index results with model release dates are available for this benchmark version.";
      return;
    }

    providerStyles = buildProviderStyles(chartPoints);
    addLegend();
    byId("avi-index-chart-status").hidden = true;
    byId("avi-index-chart-content").hidden = false;
    byId("avi-index-chart-caption").textContent =
      chartPoints.length + (chartPoints.length === 1 ? " model" : " models") +
      " · Benchmark release " + data.chart_benchmark_version +
      " · Scores are not release-day evaluations.";
    drawChart();
    installResizeObserver();
  }

  function showError(message) {
    byId("avi-index-chart-content").hidden = true;
    var status = byId("avi-index-chart-status");
    status.hidden = false;
    status.textContent = "AVI-Index trend unavailable: " + message;
  }

  byId("avi-index-chart-tooltip").addEventListener("pointerenter", function () {
    window.clearTimeout(hideTimer);
  });
  byId("avi-index-chart-tooltip").addEventListener("pointerleave", scheduleTooltipHide);
  byId("avi-index-chart-tooltip").addEventListener("focusin", function () {
    window.clearTimeout(hideTimer);
  });
  byId("avi-index-chart-tooltip").addEventListener("focusout", scheduleTooltipHide);

  window.AVIIndexChart = {
    render: render,
    showError: showError
  };
})();
