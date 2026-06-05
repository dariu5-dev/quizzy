export function initCalculator() {
  const toggleBtn = document.createElement("button");
  toggleBtn.id = "calc-toggle";
  toggleBtn.title = "Calculator";
  toggleBtn.textContent = "🧮";

  const calcEl = document.createElement("div");
  calcEl.id = "calculator";
  calcEl.classList.add("hidden");
  calcEl.innerHTML = `
    <div id="calc-display">0</div>
    <div class="calc-buttons">
      <button class="calc-btn clear" data-action="clear">C</button>
      <button class="calc-btn op" data-action="sign">+/-</button>
      <button class="calc-btn op" data-action="percent">%</button>
      <button class="calc-btn op" data-action="op" data-op="/">÷</button>

      <button class="calc-btn" data-action="digit" data-digit="7">7</button>
      <button class="calc-btn" data-action="digit" data-digit="8">8</button>
      <button class="calc-btn" data-action="digit" data-digit="9">9</button>
      <button class="calc-btn op" data-action="op" data-op="*">×</button>

      <button class="calc-btn" data-action="digit" data-digit="4">4</button>
      <button class="calc-btn" data-action="digit" data-digit="5">5</button>
      <button class="calc-btn" data-action="digit" data-digit="6">6</button>
      <button class="calc-btn op" data-action="op" data-op="-">−</button>

      <button class="calc-btn" data-action="digit" data-digit="1">1</button>
      <button class="calc-btn" data-action="digit" data-digit="2">2</button>
      <button class="calc-btn" data-action="digit" data-digit="3">3</button>
      <button class="calc-btn op" data-action="op" data-op="+">+</button>

      <button class="calc-btn" data-action="digit" data-digit="0" style="grid-column:span 2">0</button>
      <button class="calc-btn" data-action="dot">.</button>
      <button class="calc-btn eq" data-action="equals">=</button>
    </div>
  `;

  document.body.appendChild(toggleBtn);
  document.body.appendChild(calcEl);

  const display = calcEl.querySelector("#calc-display");

  let current = "0";
  let previous = null;
  let operator = null;
  let justEvaled = false;

  function updateDisplay() {
    display.textContent = current.length > 12 ? parseFloat(current).toPrecision(8) : current;
  }

  toggleBtn.addEventListener("click", () => {
    calcEl.classList.toggle("hidden");
  });

  calcEl.addEventListener("click", (e) => {
    const btn = e.target.closest("[data-action]");
    if (!btn) return;
    const action = btn.dataset.action;

    if (action === "digit") {
      const digit = btn.dataset.digit;
      if (justEvaled) { current = digit; justEvaled = false; }
      else current = current === "0" ? digit : current + digit;
      updateDisplay();

    } else if (action === "dot") {
      if (!current.includes(".")) current += ".";
      updateDisplay();

    } else if (action === "clear") {
      current = "0"; previous = null; operator = null; justEvaled = false;
      updateDisplay();

    } else if (action === "sign") {
      current = String(parseFloat(current) * -1);
      updateDisplay();

    } else if (action === "percent") {
      current = String(parseFloat(current) / 100);
      updateDisplay();

    } else if (action === "op") {
      if (operator && previous !== null && !justEvaled) {
        current = String(evaluate(parseFloat(previous), parseFloat(current), operator));
        updateDisplay();
      }
      previous = current;
      operator = btn.dataset.op;
      justEvaled = false;
      current = "0";

    } else if (action === "equals") {
      if (operator && previous !== null) {
        current = String(evaluate(parseFloat(previous), parseFloat(current), operator));
        previous = null;
        operator = null;
        justEvaled = true;
        updateDisplay();
      }
    }
  });

  // Don't steal keyboard input while user is typing in quiz fields
  document.addEventListener("keydown", (e) => {
    if (document.activeElement.tagName === "INPUT" || document.activeElement.tagName === "TEXTAREA") return;
    if (calcEl.classList.contains("hidden")) return;

    if (e.key >= "0" && e.key <= "9") {
      calcEl.querySelector(`[data-digit="${e.key}"]`).click();
    } else if (e.key === "+" || e.key === "-" || e.key === "*" || e.key === "/") {
      calcEl.querySelector(`[data-op="${e.key}"]`).click();
    } else if (e.key === "Enter" || e.key === "=") {
      calcEl.querySelector("[data-action='equals']").click();
    } else if (e.key === "Escape") {
      calcEl.querySelector("[data-action='clear']").click();
    } else if (e.key === ".") {
      calcEl.querySelector("[data-action='dot']").click();
    }
  });
}

function evaluate(a, b, op) {
  switch (op) {
    case "+": return a + b;
    case "-": return a - b;
    case "*": return a * b;
    case "/": return b !== 0 ? a / b : "Error";
  }
}
