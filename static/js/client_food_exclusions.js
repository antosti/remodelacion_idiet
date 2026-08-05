document.addEventListener('DOMContentLoaded', () => {
  const openBtn = document.getElementById('excludeIndividualFoodsBtn');
  const modal = document.getElementById('excludeFoodsModal');
  if (!openBtn || !modal) return;

  const closeButtons = modal.querySelectorAll('[data-close-exclude-foods-modal]');
  const searchInput = document.getElementById('excludeFoodsSearchInput');
  const resultsBox = document.getElementById('excludeFoodsResults');
  const excludedList = document.getElementById('individualExcludedFoodsList');
  const excludedInputs = document.getElementById('excludedProductsInputs');
  const clearBtn = document.getElementById('clearFoodExclusionsBtn');
  const searchUrl = openBtn.dataset.searchUrl;

  let excludedFoods = [];
  let lastResults = [];
  let searchTimeout = null;

  const initialDataEl = document.getElementById('existing-excluded-products');
  if (initialDataEl) {
    try {
      excludedFoods = JSON.parse(initialDataEl.textContent) || [];
    } catch (error) {
      excludedFoods = [];
    }
  }

  const setBodyScroll = () => {
    document.body.classList.toggle('overflow-hidden', !modal.classList.contains('hidden'));
  };

  const isExcluded = (id) => excludedFoods.some((food) => food.id === id);

  function syncExcludedInputs() {
    if (!excludedInputs) return;

    excludedInputs.innerHTML = '';
    excludedFoods.forEach((food) => {
      const input = document.createElement('input');
      input.type = 'hidden';
      input.name = 'excluded_products';
      input.value = food.id;
      excludedInputs.appendChild(input);
    });
  }

  function renderExcludedList() {
    syncExcludedInputs();

    if (!excludedList) return;

    if (excludedFoods.length === 0) {
      excludedList.innerHTML = '<p class="px-3 py-2 text-sm text-gray-400">Todavía no se ha excluido ningún alimento individualmente.</p>';
      return;
    }

    excludedList.innerHTML = '';

    excludedFoods.forEach((food) => {
      const item = document.createElement('div');
      item.className = 'flex items-center justify-between px-3 py-2 rounded-lg bg-gray-50 border border-gray-200';

      const name = document.createElement('span');
      name.className = 'text-sm text-gray-700';
      name.textContent = food.name;

      const removeBtn = document.createElement('button');
      removeBtn.type = 'button';
      removeBtn.className = 'text-red-600 hover:text-red-800 font-bold text-sm';
      removeBtn.textContent = '✕';
      removeBtn.addEventListener('click', () => {
        excludedFoods = excludedFoods.filter((food_) => food_.id !== food.id);
        renderExcludedList();
        renderResults(lastResults);
      });

      item.appendChild(name);
      item.appendChild(removeBtn);
      excludedList.appendChild(item);
    });
  }

  function renderResults(results) {
    lastResults = results;
    resultsBox.innerHTML = '';

    if (!results.length) {
      resultsBox.innerHTML = '<p class="px-3 py-6 text-center text-sm text-gray-400">No se han encontrado alimentos.</p>';
      return;
    }

    results.forEach((product) => {
      const row = document.createElement('div');
      row.className = 'flex items-center justify-between px-3 py-2 rounded-lg hover:bg-gray-50';

      const name = document.createElement('span');
      name.className = 'text-sm text-gray-700';
      name.textContent = `${product.name} (${product.kcal_100g} kcal/100g)`;

      const actionBtn = document.createElement('button');
      actionBtn.type = 'button';

      if (isExcluded(product.id)) {
        actionBtn.textContent = 'Excluido';
        actionBtn.disabled = true;
        actionBtn.className = 'px-3 py-1 rounded-lg border border-gray-200 bg-gray-100 text-gray-400 text-xs font-semibold cursor-not-allowed';
      } else {
        actionBtn.textContent = 'Excluir';
        actionBtn.className = 'px-3 py-1 rounded-lg border border-red-300 text-red-600 text-xs font-semibold hover:bg-red-50';
        actionBtn.addEventListener('click', () => {
          excludedFoods.push({ id: product.id, name: product.name });
          renderExcludedList();
          renderResults(lastResults);
        });
      }

      row.appendChild(name);
      row.appendChild(actionBtn);
      resultsBox.appendChild(row);
    });
  }

  function fetchProducts(query) {
    fetch(`${searchUrl}?q=${encodeURIComponent(query || '')}`)
      .then((response) => response.json())
      .then((data) => renderResults(data.results || []))
      .catch(() => renderResults([]));
  }

  function openModal() {
    modal.classList.remove('hidden');
    setBodyScroll();
    fetchProducts(searchInput ? searchInput.value.trim() : '');
  }

  function closeModal() {
    modal.classList.add('hidden');
    setBodyScroll();
  }

  openBtn.addEventListener('click', openModal);
  closeButtons.forEach((button) => button.addEventListener('click', closeModal));

  if (searchInput) {
    searchInput.addEventListener('input', () => {
      const query = searchInput.value.trim();
      if (searchTimeout) clearTimeout(searchTimeout);
      searchTimeout = setTimeout(() => fetchProducts(query), 300);
    });
  }

  if (clearBtn) {
    clearBtn.addEventListener('click', () => {
      excludedFoods = [];
      renderExcludedList();
      renderResults(lastResults);
    });
  }

  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape') closeModal();
  });

  renderExcludedList();
});

document.addEventListener('DOMContentLoaded', () => {
  const availableList = document.getElementById('availableFoodGroupsList');
  const excludedList = document.getElementById('excludedFoodGroupsList');
  if (!availableList || !excludedList) return;

  const excludedInputs = document.getElementById('excludedFoodGroupsInputs');
  const clearBtn = document.getElementById('clearFoodExclusionsBtn');
  const groupButtons = Array.from(availableList.querySelectorAll('.food-group-btn'));
  const filterAvailableInput = document.getElementById('filterAvailableFoodGroups');
  const filterExcludedInput = document.getElementById('filterExcludedFoodGroups');

  let excludedGroups = [];
  let availableFilterText = '';
  let excludedFilterText = '';

  const initialDataEl = document.getElementById('existing-excluded-food-groups');
  if (initialDataEl) {
    try {
      excludedGroups = JSON.parse(initialDataEl.textContent) || [];
    } catch (error) {
      excludedGroups = [];
    }
  }

  const isExcluded = (id) => excludedGroups.some((group) => group.id === id);

  function syncExcludedInputs() {
    if (!excludedInputs) return;

    excludedInputs.innerHTML = '';
    excludedGroups.forEach((group) => {
      const input = document.createElement('input');
      input.type = 'hidden';
      input.name = 'excluded_food_groups';
      input.value = group.id;
      excludedInputs.appendChild(input);
    });
  }

  function renderAvailableButtons() {
    groupButtons.forEach((button) => {
      const id = Number(button.dataset.value);
      const excluded = isExcluded(id);
      button.disabled = excluded;
      button.classList.toggle('opacity-40', excluded);
      button.classList.toggle('cursor-not-allowed', excluded);

      const name = (button.dataset.name || '').toLowerCase();
      const matchesFilter = !availableFilterText || name.includes(availableFilterText);
      button.classList.toggle('hidden', !matchesFilter);
    });
  }

  function renderExcludedList() {
    syncExcludedInputs();
    renderAvailableButtons();

    if (excludedGroups.length === 0) {
      excludedList.innerHTML = '<p class="px-3 py-2 text-sm text-gray-400">Aquí aparecerán los grupos excluidos</p>';
      return;
    }

    const filteredGroups = excludedGroups.filter((group) =>
      !excludedFilterText || group.name.toLowerCase().includes(excludedFilterText)
    );

    if (filteredGroups.length === 0) {
      excludedList.innerHTML = '<p class="px-3 py-2 text-sm text-gray-400">No se han encontrado grupos excluidos.</p>';
      return;
    }

    excludedList.innerHTML = '';

    filteredGroups.forEach((group) => {
      const item = document.createElement('div');
      item.className = 'flex items-center justify-between px-3 py-2 rounded-lg bg-gray-50 border border-gray-200';

      const name = document.createElement('span');
      name.className = 'text-sm text-gray-700';
      name.textContent = group.name;

      const removeBtn = document.createElement('button');
      removeBtn.type = 'button';
      removeBtn.className = 'text-red-600 hover:text-red-800 font-bold text-sm';
      removeBtn.textContent = '✕';
      removeBtn.addEventListener('click', () => {
        excludedGroups = excludedGroups.filter((group_) => group_.id !== group.id);
        renderExcludedList();
      });

      item.appendChild(name);
      item.appendChild(removeBtn);
      excludedList.appendChild(item);
    });
  }

  groupButtons.forEach((button) => {
    button.addEventListener('click', () => {
      const id = Number(button.dataset.value);
      if (isExcluded(id)) return;
      excludedGroups.push({ id, name: button.dataset.name });
      renderExcludedList();
    });
  });

  if (clearBtn) {
    clearBtn.addEventListener('click', () => {
      excludedGroups = [];
      renderExcludedList();
    });
  }

  if (filterAvailableInput) {
    filterAvailableInput.addEventListener('input', () => {
      availableFilterText = filterAvailableInput.value.trim().toLowerCase();
      renderAvailableButtons();
    });
  }

  if (filterExcludedInput) {
    filterExcludedInput.addEventListener('input', () => {
      excludedFilterText = filterExcludedInput.value.trim().toLowerCase();
      renderExcludedList();
    });
  }

  renderExcludedList();
});
