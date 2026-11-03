// Seat picker for seats.html.
// Clicking an available seat selects or unselects it (up to MAX_SEATS).
// The summary list, total, hidden seat_ids inputs and Continue button are
// rebuilt from the `selected` list after every click.
(function () {
  var MAX_SEATS = 6;
  var form = document.getElementById("seat-form");
  if (!form) return;

  var inputs = document.getElementById("seat-inputs");
  var list = document.getElementById("selected-list");
  var totalEl = document.getElementById("selected-total");
  var countEl = document.getElementById("selected-count");
  var limitMsg = document.getElementById("limit-msg");
  var continueBtn = document.getElementById("continue-btn");
  var seatButtons = Array.prototype.slice.call(document.querySelectorAll(".seat-map .seat"));
  var selected = []; // the seat buttons currently selected

  function rupees(amount) {
    return "₹" + amount.toLocaleString("en-IN", { maximumFractionDigits: 0 });
  }

  function render() {
    // Keep seats in the order they appear on the map (A1, A2 ... H8).
    selected.sort(function (a, b) { return seatButtons.indexOf(a) - seatButtons.indexOf(b); });

    inputs.innerHTML = "";
    list.innerHTML = "";
    var total = 0;

    selected.forEach(function (seat) {
      var price = parseFloat(seat.dataset.price);
      total += price;

      var input = document.createElement("input");
      input.type = "hidden";
      input.name = "seat_ids";
      input.value = seat.dataset.seatId;
      inputs.appendChild(input);

      var item = document.createElement("li");
      item.className = "d-flex justify-content-between";
      var label = document.createElement("span");
      label.textContent = seat.dataset.label;
      var cost = document.createElement("span");
      cost.textContent = rupees(price);
      item.appendChild(label);
      item.appendChild(cost);
      list.appendChild(item);
    });

    if (selected.length === 0) {
      var empty = document.createElement("li");
      empty.className = "text-muted";
      empty.textContent = "Tap a seat to select it.";
      list.appendChild(empty);
    }

    totalEl.textContent = rupees(total);
    countEl.textContent = selected.length;
    limitMsg.hidden = selected.length < MAX_SEATS;
    continueBtn.disabled = selected.length === 0;
  }

  seatButtons.forEach(function (seat) {
    if (seat.disabled) return; // taken seats are disabled in the template

    seat.addEventListener("click", function () {
      var index = selected.indexOf(seat);
      if (index !== -1) {
        selected.splice(index, 1);
        seat.classList.remove("is-selected");
        seat.setAttribute("aria-pressed", "false");
      } else if (selected.length < MAX_SEATS) {
        selected.push(seat);
        seat.classList.add("is-selected");
        seat.setAttribute("aria-pressed", "true");
      } else {
        limitMsg.hidden = false;
        return;
      }
      render();
    });
  });

  render();
})();
