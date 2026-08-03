document.addEventListener('DOMContentLoaded', () => {
  const container = document.querySelector('[data-ingredients-app]');
  if (!container) return;

  const searchInput = container.querySelector('#ingredientSearchInput');
  const resultsBox = container.querySelector('#ingredientSearchResults');
  const tbody = container.querySelector('#ingredientsTableBody');
  const searchUrl = container.dataset.searchUrl;

  const kcalField = document.getElementById('dishKcalField');
  const carbsField = document.getElementById('dishCarbsField');
  const proteinField = document.getElementById('dishProteinField');
  const fatField = document.getElementById('dishFatField');

  let ingredients = [];
  let searchTimeout = null;

  const initialDataEl = document.getElementById('existing-ingredients');

  if (initialDataEl) {
    try {
      ingredients = JSON.parse(initialDataEl.textContent) || [];
    } catch (error) {
      ingredients = [];
    }
  }

  function renderTable() {
    tbody.innerHTML = '';

    if (ingredients.length === 0) {
      const emptyRow = document.createElement('tr');
      emptyRow.innerHTML = `
        <td colspan="4" class="px-4 py-6 text-center text-sm text-gray-500 border-b border-gray-100">
          Esta receta no tiene ingredientes registrados.
        </td>
      `;
      tbody.appendChild(emptyRow);
      return;
    }

    ingredients.forEach((ingredient, index) => {
      const row = document.createElement('tr');
      row.className = 'hover:bg-gray-50';

      const nameCell = document.createElement('td');
      nameCell.className = 'px-4 py-4 text-gray-700 border-b border-gray-100';
      nameCell.textContent = ingredient.name;

      const hiddenProductId = document.createElement('input');
      hiddenProductId.type = 'hidden';
      hiddenProductId.name = 'ingredient_product_id';
      hiddenProductId.value = ingredient.id;
      nameCell.appendChild(hiddenProductId);

      const quantityCell = document.createElement('td');
      quantityCell.className = 'px-4 py-4 text-gray-700 border-b border-gray-100';

      const quantityInput = document.createElement('input');
      quantityInput.type = 'number';
      quantityInput.min = '1';
      quantityInput.step = '1';
      quantityInput.name = 'ingredient_quantity';
      quantityInput.value = ingredient.quantity;
      quantityInput.className = 'w-24 border rounded-lg px-2 py-1 focus:outline-none focus:ring-2 focus:ring-secondary/30';
      quantityInput.addEventListener('input', () => {
        const value = parseInt(quantityInput.value, 10);
        ingredients[index].quantity = Number.isFinite(value) && value > 0 ? value : 0;
        renderTotals();
      });

      quantityCell.appendChild(quantityInput);

      const kcalCell = document.createElement('td');
      kcalCell.className = 'px-4 py-4 text-gray-700 border-b border-gray-100';
      kcalCell.textContent = ingredient.kcal_100g;

      const removeCell = document.createElement('td');
      removeCell.className = 'px-4 py-4 border-b border-gray-100 text-right';

      const removeBtn = document.createElement('button');
      removeBtn.type = 'button';
      removeBtn.className = 'text-red-600 hover:text-red-800 font-bold';
      removeBtn.textContent = '✕';
      removeBtn.addEventListener('click', () => {
        ingredients.splice(index, 1);
        renderTable();
        renderTotals();
      });

      removeCell.appendChild(removeBtn);

      row.appendChild(nameCell);
      row.appendChild(quantityCell);
      row.appendChild(kcalCell);
      row.appendChild(removeCell);

      tbody.appendChild(row);
    });
  }

  function renderTotals() {
    let totalQuantity = 0;
    let totalKcal = 0;
    let totalCarbs = 0;
    let totalProtein = 0;
    let totalFat = 0;

    ingredients.forEach((ingredient) => {
      const quantity = ingredient.quantity || 0;

      totalQuantity += quantity;
      totalKcal += (ingredient.kcal_100g || 0) * quantity / 100;
      totalCarbs += (ingredient.ch_g || 0) * quantity / 100;
      totalProtein += (ingredient.prot_g || 0) * quantity / 100;
      totalFat += (ingredient.fat_g || 0) * quantity / 100;
    });

    const kcal100g = totalQuantity ? (totalKcal / totalQuantity * 100) : 0;
    const carbs100g = totalQuantity ? (totalCarbs / totalQuantity * 100) : 0;
    const protein100g = totalQuantity ? (totalProtein / totalQuantity * 100) : 0;
    const fat100g = totalQuantity ? (totalFat / totalQuantity * 100) : 0;

    if (kcalField) kcalField.value = kcal100g.toFixed(2);
    if (carbsField) carbsField.value = carbs100g.toFixed(2);
    if (proteinField) proteinField.value = protein100g.toFixed(2);
    if (fatField) fatField.value = fat100g.toFixed(2);
  }

  function addIngredient(product) {
    const existing = ingredients.find((ingredient) => ingredient.id === product.id);

    if (existing) {
      existing.quantity += 100;
    } else {
      ingredients.push({
        id: product.id,
        name: product.name,
        kcal_100g: product.kcal_100g,
        ch_g: product.ch_g,
        prot_g: product.prot_g,
        fat_g: product.fat_g,
        quantity: 100,
      });
    }

    renderTable();
    renderTotals();
  }

  function renderSearchResults(results) {
    resultsBox.innerHTML = '';

    if (!results.length) {
      resultsBox.classList.add('hidden');
      return;
    }

    results.forEach((product) => {
      const item = document.createElement('button');
      item.type = 'button';
      item.className = 'block w-full text-left px-3 py-2 text-sm hover:bg-gray-100';
      item.textContent = `${product.name} (${product.kcal_100g} kcal/100g)`;
      item.addEventListener('click', () => {
        addIngredient(product);
        resultsBox.classList.add('hidden');
        searchInput.value = '';
      });

      resultsBox.appendChild(item);
    });

    resultsBox.classList.remove('hidden');
  }

  if (searchInput) {
    searchInput.addEventListener('input', () => {
      const query = searchInput.value.trim();

      if (searchTimeout) clearTimeout(searchTimeout);

      if (query.length < 2) {
        resultsBox.classList.add('hidden');
        return;
      }

      searchTimeout = setTimeout(() => {
        fetch(`${searchUrl}?q=${encodeURIComponent(query)}`)
          .then((response) => response.json())
          .then((data) => renderSearchResults(data.results || []))
          .catch(() => resultsBox.classList.add('hidden'));
      }, 300);
    });

    document.addEventListener('click', (event) => {
      if (!container.contains(event.target)) {
        resultsBox.classList.add('hidden');
      }
    });
  }

  renderTable();
  renderTotals();
});
