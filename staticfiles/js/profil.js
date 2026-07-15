document.addEventListener("DOMContentLoaded", () => {
  function dropdownMenu() {
    let container = document.querySelector(".container_box");
    let drop = document.querySelector(".drop_box");
    let btn = document.querySelector("#btn_");
    let close = document.querySelector(".close");

    container.style.display = "none";

    close.addEventListener("click", () => {
      container.style.display = "none";
    });

    btn.addEventListener("click", () => {
      if (container.style.display == "none") {
        container.style.display = "block";
        drop.style.display = "block";
      } else {
        container.style.display = "none";
        drop.style.display = "none";
      }
    });
  }
  dropdownMenu();
});
