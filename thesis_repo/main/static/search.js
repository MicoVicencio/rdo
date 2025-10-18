document.addEventListener("DOMContentLoaded", () => {
  const searchInput = document.getElementById("search-input");
  const filterCourse = document.getElementById("filter-course");
  const filterYear = document.getElementById("filter-year");
  const resultBody = document.getElementById("result-body");
  const filterContainer = document.getElementById("active-filters");
  let timer;

  function updateFiltersDisplay() {
    filterContainer.innerHTML = "";
    const course = filterCourse.value;
    const year = filterYear.value;
    const query = searchInput.value.trim();

    if (query)
      filterContainer.innerHTML += `<span class="filter-chip">🔍 ${query}</span>`;
    if (course)
      filterContainer.innerHTML += `<span class="filter-chip">📚 ${course}</span>`;
    if (year)
      filterContainer.innerHTML += `<span class="filter-chip">📅 ${year}</span>`;
  }

  function fetchResults() {
    const query = searchInput.value.trim();
    const course = filterCourse.value;
    const year = filterYear.value;

    updateFiltersDisplay();

    fetch(
      `/api/search?query=${encodeURIComponent(query)}&course=${encodeURIComponent(
        course
      )}&year=${encodeURIComponent(year)}`
    )
      .then((res) => res.json())
      .then((data) => {
        resultBody.innerHTML = "";
        if (data.length === 0) {
          resultBody.innerHTML = `<tr><td colspan="4" style="text-align:center;color:gray;padding:15px;">No results found.</td></tr>`;
          return;
        }

        data.forEach((d) => {
          const row = document.createElement("tr");
          row.innerHTML = `
            <td>${d.title}</td>
            <td>${d.course}</td>
            <td>${d.year || "-"}</td>
            <td>${d.date_uploaded}</td>
          `;
          row.addEventListener("click", () => showDetailModal(d));
          resultBody.appendChild(row);
        });
      })
      .catch((err) => console.error("Error fetching results:", err));
  }

  // --- Detail modal setup ---
  const detailModal = document.getElementById("detail-modal");
  const modalTitle = document.getElementById("modal-title");
  const modalAuthors = document.getElementById("modal-authors");
  const modalCourse = document.getElementById("modal-course");
  const modalYear = document.getElementById("modal-year");
  const modalKeywords = document.getElementById("modal-keywords");
  const modalAbstractContainer = document.getElementById("modal-abstract-container");
  const closeModalBtn = document.getElementById("close-modal");

  // --- Show modal details ---
  function showDetailModal(data) {
    modalTitle.textContent = data.title;
    modalAuthors.textContent = data.authors || "-";
    modalCourse.textContent = data.course;
    modalYear.textContent = data.year || "-";
    modalKeywords.textContent = data.keywords || "-";

    // Clear previous abstract images
    modalAbstractContainer.innerHTML = "";
    if (data.pdf_path) {
      fetch(`/get_abstract_image?pdf=${encodeURIComponent(data.pdf_path)}`)
        .then((res) => res.json())
        .then((json) => {
          if (json.images && json.images.length > 0) {
            json.images.forEach((base64Img) => {
              const img = document.createElement("img");
              img.src = `data:image/png;base64,${base64Img}`;
              img.alt = "Abstract page";
              img.style.width = "100%";
              img.style.marginBottom = "10px";
              modalAbstractContainer.appendChild(img);
            });
          } else {
            modalAbstractContainer.innerHTML = `<p style="color:gray;">No abstract image available.</p>`;
          }
        })
        .catch((err) => {
          console.error("Error loading abstract images:", err);
          modalAbstractContainer.innerHTML = `<p style="color:gray;">No abstract image available.</p>`;
        });
    } else {
      modalAbstractContainer.innerHTML = `<p style="color:gray;">No abstract image available.</p>`;
    }

    detailModal.classList.add("active");
  }

  // --- Close modal ---
  closeModalBtn.addEventListener("click", () =>
    detailModal.classList.remove("active")
  );

  searchInput.addEventListener("input", () => {
    clearTimeout(timer);
    timer = setTimeout(fetchResults, 200);
  });

  [filterCourse, filterYear].forEach((el) =>
    el.addEventListener("change", fetchResults)
  );

  fetchResults();
});
