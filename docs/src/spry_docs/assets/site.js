const menuButton = document.querySelector("[data-menu-button]");
const menuClose = document.querySelector("[data-menu-close]");
const mobileNav = document.querySelector("[data-mobile-nav]");

function openMenu() {
  if (mobileNav) {
    mobileNav.classList.add("is-open");
  }
}

function closeMenu() {
  if (mobileNav) {
    mobileNav.classList.remove("is-open");
  }
}

if (menuButton) {
  menuButton.addEventListener("click", openMenu);
}

if (menuClose) {
  menuClose.addEventListener("click", closeMenu);
}

if (mobileNav) {
  mobileNav.addEventListener("click", (event) => {
    if (event.target === mobileNav) {
      closeMenu();
    }
  });

  mobileNav.querySelectorAll("a").forEach((link) => {
    link.addEventListener("click", closeMenu);
  });
}
