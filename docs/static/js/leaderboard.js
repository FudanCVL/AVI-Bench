(function () {
  "use strict";

  var LOGO_BY_PROVIDER = {
    google: "leaderboard/assets/logos/google.svg",
    qwen: "leaderboard/assets/logos/qwen.jpg",
    openai: "leaderboard/assets/logos/openai.svg"
  };

  var TABLES = [
    {
      id: "stage-table",
      columns: [
        { key: "rank", label: "Rank", kind: "rank" },
        { key: "model_name", label: "Model", kind: "model" },
        { key: "overall", label: "Overall", kind: "score", path: ["scores", "overall"] },
        { key: "perception", label: "Perception", kind: "score", path: ["scores", "stages", "perception"] },
        { key: "understanding", label: "Understanding", kind: "score", path: ["scores", "stages", "understanding"] },
        { key: "reasoning", label: "Reasoning", kind: "score", path: ["scores", "stages", "reasoning"] },
        { key: "sensation", label: "Primitive Sensation", kind: "score", path: ["scores", "stages", "sensation"] }
      ],
      state: { activeKey: "overall", direction: -1 }
    },
    {
      id: "taxonomy-table",
      columns: [
        { key: "rank", label: "Rank", kind: "rank" },
        { key: "model_name", label: "Model", kind: "model" },
        { key: "l1_task", label: "Task-Adaptive", kind: "score", path: ["scores", "taxonomy", "l1_task"] },
        { key: "l2_modality", label: "Modality-Adaptive", kind: "score", path: ["scores", "taxonomy", "l2_modality"] },
        { key: "l3_stage", label: "Stage-Adaptive", kind: "score", path: ["scores", "taxonomy", "l3_stage"] },
        { key: "l4_domain", label: "Domain-Adaptive", kind: "score", path: ["scores", "taxonomy", "l4_domain"] }
      ],
      state: { activeKey: "l4_domain", direction: -1 }
    }
  ];

  var entries = [];

  function readPath(object, path) {
    return path.reduce(function (value, key) {
      return value && value[key] !== undefined ? value[key] : null;
    }, object);
  }

  function formatScore(value) {
    return typeof value === "number" && Number.isFinite(value) ? value.toFixed(2) : "—";
  }

  function compareText(left, right) {
    return String(left || "").localeCompare(String(right || ""), undefined, {
      numeric: true,
      sensitivity: "base"
    });
  }

  function compareEntries(left, right, table) {
    var leftValue = readPath(left, table.state.sortColumn.path);
    var rightValue = readPath(right, table.state.sortColumn.path);
    var leftMissing = leftValue === null || leftValue === undefined;
    var rightMissing = rightValue === null || rightValue === undefined;

    if (leftMissing !== rightMissing) {
      return leftMissing ? 1 : -1;
    }

    if (!leftMissing && typeof leftValue === "number" && typeof rightValue === "number") {
      if (leftValue !== rightValue) {
        return (leftValue - rightValue) * table.state.direction;
      }
    } else if (!leftMissing) {
      var textOrder = compareText(leftValue, rightValue);
      if (textOrder !== 0) {
        return textOrder * table.state.direction;
      }
    }

    return compareText(left.model_name, right.model_name);
  }

  function makeCell(value, className) {
    var cell = document.createElement("td");
    if (className) {
      cell.className = className;
    }
    cell.textContent = value;
    return cell;
  }

  function providerLogo(provider) {
    var providerKey = String(provider || "").trim().toLowerCase();
    var source = LOGO_BY_PROVIDER[providerKey];
    var wrapper = document.createElement("span");
    wrapper.className = source ? "provider-logo" : "provider-fallback";
    wrapper.setAttribute("aria-hidden", "true");

    if (!source) {
      wrapper.textContent = String(provider || "?").trim().slice(0, 1).toUpperCase();
      return wrapper;
    }

    if (providerKey === "qwen") {
      wrapper.classList.add("provider-logo-qwen");
    }

    var image = document.createElement("img");
    image.src = source;
    image.alt = "";
    image.addEventListener("error", function () {
      var fallback = document.createElement("span");
      fallback.className = "provider-fallback";
      fallback.setAttribute("aria-hidden", "true");
      fallback.textContent = String(provider || "?").trim().slice(0, 1).toUpperCase();
      wrapper.replaceWith(fallback);
    }, { once: true });
    wrapper.appendChild(image);
    return wrapper;
  }

  function createModelCell(entry) {
    var cell = document.createElement("td");
    var content = document.createElement("div");
    content.className = "model-cell";
    content.appendChild(providerLogo(entry.provider));

    var info = document.createElement("div");
    info.className = "model-info";

    var name = document.createElement("span");
    name.className = "model-name";
    name.textContent = entry.model_name;

    var provider = document.createElement("span");
    provider.className = "model-provider";
    provider.textContent = entry.provider;

    info.appendChild(name);
    info.appendChild(provider);
    content.appendChild(info);
    cell.appendChild(content);
    return cell;
  }

  function renderHeader(table) {
    var header = document.querySelector("#" + table.id + " thead tr");
    header.replaceChildren();

    table.columns.forEach(function (column) {
      var cell = document.createElement("th");
      cell.scope = "col";

      if (column.kind !== "score") {
        cell.textContent = column.label;
        header.appendChild(cell);
        return;
      }

      var button = document.createElement("button");
      button.className = "sort-button";
      button.type = "button";
      button.dataset.sortKey = column.key;
      button.setAttribute("aria-label", "Sort by " + column.label);

      var label = document.createElement("span");
      label.textContent = column.label;

      var mark = document.createElement("span");
      mark.className = "sort-mark";
      mark.setAttribute("aria-hidden", "true");
      mark.textContent = "↕";

      button.appendChild(label);
      button.appendChild(mark);
      button.addEventListener("click", function () {
        if (table.state.activeKey === column.key) {
          table.state.direction *= -1;
        } else {
          table.state.direction = -1;
        }
        table.state.activeKey = column.key;
        table.state.sortColumn = column;
        renderTable(table);
      });

      cell.appendChild(button);
      header.appendChild(cell);
    });
  }

  function renderTable(table) {
    var element = document.getElementById(table.id);
    var body = element.querySelector("tbody");
    var visible = entries.slice().sort(function (left, right) {
      return compareEntries(left, right, table);
    });

    body.replaceChildren();

    if (!visible.length) {
      var emptyRow = document.createElement("tr");
      var emptyCell = document.createElement("td");
      emptyCell.className = "empty-cell";
      emptyCell.colSpan = table.columns.length;
      emptyCell.textContent = "No results published yet.";
      emptyRow.appendChild(emptyCell);
      body.appendChild(emptyRow);
    }

    visible.forEach(function (entry, index) {
      var row = document.createElement("tr");
      row.className = "data-row";

      table.columns.forEach(function (column) {
        if (column.kind === "rank") {
          row.appendChild(makeCell(String(index + 1), "rank-value"));
          return;
        }

        if (column.kind === "model") {
          row.appendChild(createModelCell(entry));
          return;
        }

        var value = readPath(entry, column.path);
        var classes = column.key === "overall" ? "score score-overall" : "score";
        if (column.key === table.state.activeKey) {
          classes += " score-selected";
        }
        row.appendChild(makeCell(formatScore(value), classes));
      });

      body.appendChild(row);
    });

    element.querySelectorAll(".sort-button").forEach(function (button) {
      button.removeAttribute("aria-sort");
      button.querySelector(".sort-mark").textContent = "↕";
    });

    var activeButton = element.querySelector('[data-sort-key="' + table.state.activeKey + '"]');
    if (activeButton) {
      activeButton.setAttribute(
        "aria-sort",
        table.state.direction === -1 ? "descending" : "ascending"
      );
      activeButton.querySelector(".sort-mark").textContent =
        table.state.direction === -1 ? "↓" : "↑";
    }

    var count = document.querySelector('[data-count-for="' + table.id + '"]');
    count.textContent = visible.length + (visible.length === 1 ? " model" : " models");
  }

  function showError(message) {
    document.getElementById("global-count").textContent = "results unavailable";

    TABLES.forEach(function (table) {
      var body = document.querySelector("#" + table.id + " tbody");
      body.replaceChildren();

      var row = document.createElement("tr");
      var cell = document.createElement("td");
      cell.className = "error-cell";
      cell.colSpan = table.columns.length;
      cell.textContent = message;
      row.appendChild(cell);
      body.appendChild(row);

      document.querySelector('[data-count-for="' + table.id + '"]').textContent = "Unavailable";
    });
  }

  TABLES.forEach(function (table) {
    table.state.sortColumn = table.columns.find(function (column) {
      return column.key === table.state.activeKey;
    });
    renderHeader(table);
  });

  fetch("leaderboard/data/results.json", { cache: "no-store" })
    .then(function (response) {
      if (!response.ok) {
        throw new Error("Could not load leaderboard data (HTTP " + response.status + ").");
      }
      return response.json();
    })
    .then(function (data) {
      if (
        !data ||
        data.schema_version !== 2 ||
        typeof data.chart_benchmark_version !== "string" ||
        !Array.isArray(data.entries)
      ) {
        throw new Error("Leaderboard data does not match the expected schema.");
      }

      entries = data.entries;
      if (window.AVIIndexChart) {
        try {
          window.AVIIndexChart.render(data);
        } catch (chartError) {
          window.AVIIndexChart.showError("Chart rendering failed.");
        }
      } else {
        document.getElementById("avi-index-chart-status").textContent =
          "AVI-Index trend unavailable: chart script could not be loaded.";
      }
      document.getElementById("global-count").textContent =
        entries.length + (entries.length === 1 ? " model result" : " model results");
      TABLES.forEach(renderTable);
    })
    .catch(function (error) {
      if (window.AVIIndexChart) {
        window.AVIIndexChart.showError(error.message || "Could not load leaderboard data.");
      }
      showError(error.message || "Could not load leaderboard data.");
    });
})();
