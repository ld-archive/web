/* ===================================================================
 * archive-search.js — client-side browse + search for the LD Archive
 *
 * Operates entirely on the server-rendered .record-card elements, so
 * the archive still lists every record with JavaScript disabled; the
 * search box and facet filters are progressive enhancements.
 * No external libraries, no network requests.
 * =================================================================== */

(function () {
	"use strict";

	var controls = document.getElementById("archive-controls");
	var input = document.getElementById("archive-search-input");
	var facetDesigner = document.getElementById("facet-designer");
	var facetVenue = document.getElementById("facet-venue");
	var facetYear = document.getElementById("facet-year");
	var resultCount = document.getElementById("result-count");
	var noResults = document.getElementById("no-results");
	var cards = Array.prototype.slice.call(
		document.querySelectorAll(".record-card")
	);

	if (!controls || !cards.length) {
		return;
	}

	/* Reveal the controls now that JS is running. */
	controls.hidden = false;

	/* ===== Populate the facet dropdowns from the rendered cards ===== */

	function addOptions(select, values, descending) {
		var unique = Object.keys(
			values.reduce(function (set, v) {
				if (v) {
					set[v] = true;
				}
				return set;
			}, {})
		);
		unique.sort(function (a, b) {
			if (descending) {
				return b.localeCompare(a, undefined, { numeric: true });
			}
			return a.localeCompare(b, undefined, { numeric: true });
		});
		unique.forEach(function (v) {
			var opt = document.createElement("option");
			opt.value = v;
			opt.textContent = v;
			select.appendChild(opt);
		});
	}

	var designers = [];
	var venues = [];
	var years = [];

	cards.forEach(function (card) {
		var display = card.getAttribute("data-designers-display") || "";
		display.split("||").forEach(function (name) {
			if (name) {
				designers.push(name);
			}
		});
		venues.push(card.getAttribute("data-venue") || "");
		years.push(card.getAttribute("data-year") || "");
	});

	addOptions(facetDesigner, designers, false);
	addOptions(facetVenue, venues, false);
	addOptions(facetYear, years, true);

	/* ===== Filtering ===== */

	function matchesCard(card, query, designer, venue, year) {
		if (query) {
			var haystack = card.getAttribute("data-search") || "";
			if (haystack.indexOf(query) === -1) {
				return false;
			}
		}
		if (designer) {
			var cardDesigners = "||" + (card.getAttribute("data-designers") || "") + "||";
			if (cardDesigners.indexOf("||" + designer.toLowerCase() + "||") === -1) {
				return false;
			}
		}
		if (venue && card.getAttribute("data-venue") !== venue) {
			return false;
		}
		if (year && card.getAttribute("data-year") !== year) {
			return false;
		}
		return true;
	}

	function applyFilters() {
		var query = input.value.trim().toLowerCase();
		var designer = facetDesigner.value;
		var venue = facetVenue.value;
		var year = facetYear.value;
		var shown = 0;

		cards.forEach(function (card) {
			var visible = matchesCard(card, query, designer, venue, year);
			card.hidden = !visible;
			if (visible) {
				shown += 1;
			}
		});

		var total = cards.length;
		if (shown === total) {
			resultCount.textContent = "Showing all " + total + " records.";
		} else {
			resultCount.textContent = "Showing " + shown + " of " + total + " records.";
		}
		noResults.hidden = shown !== 0;
	}

	function clearFilters() {
		input.value = "";
		facetDesigner.value = "";
		facetVenue.value = "";
		facetYear.value = "";
		applyFilters();
		input.focus();
	}

	/* ===== Wire up events ===== */

	input.addEventListener("input", applyFilters);
	facetDesigner.addEventListener("change", applyFilters);
	facetVenue.addEventListener("change", applyFilters);
	facetYear.addEventListener("change", applyFilters);

	var clearButtons = document.querySelectorAll(".clear-filters");
	Array.prototype.forEach.call(clearButtons, function (btn) {
		btn.addEventListener("click", clearFilters);
	});

	applyFilters();
})();
