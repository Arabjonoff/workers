"use stict";

document.addEventListener("DOMContentLoaded", () => {
  const btn = document.querySelector(".btn__");
  const box = document.querySelector(".id_js");

  box.style.display = "none";

  btn.addEventListener("click", () => {
    if (box.style.display == "none") {
      box.style.display = "block";
      btn.style.transform = "rotate(180deg)";
    } else {
      box.style.display = "none";
      btn.style.transform = "rotate(360deg)";
    }
  });
});
