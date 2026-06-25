document.addEventListener('DOMContentLoaded', () => {
  const tabDescription = document.getElementById('tab-description');
  const userTypeInput = document.getElementById('user_type');
  const tabButtons = document.querySelectorAll('.tab-btn');

  function setActiveTab(tab) {
    tabButtons.forEach((button) => {
      const isActive = button.dataset.tab === tab;
      button.classList.toggle('bg-idiet', isActive);
      button.classList.toggle('text-white', isActive);
      button.classList.toggle('shadow-sm', isActive);
      button.classList.toggle('bg-secondary/10', !isActive);
      button.classList.toggle('text-idiet', !isActive);
      button.classList.toggle('hover:bg-secondary/20', !isActive);
      button.classList.toggle('hover:bg-idiet/90', isActive);
    });

    if (tab === 'formacion') {
      userTypeInput.value = 'formacion';
    } else {
      userTypeInput.value = 'clientes';
    }
  }

  window.changeTab = (tab) => {
    setActiveTab(tab);
  };

  setActiveTab('clientes');
});
