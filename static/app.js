const container=document.querySelector(".container");
const registerBtn=document.querySelector(".register-btn");
const loginBtn=document.querySelector(".login-btn");

registerBtn.addEventListener("click",()=>{
    container.classList.add("active");
});

loginBtn.addEventListener("click",()=>{
    container.classList.remove("active");
}); 
// Popup form script
const popup = document.getElementById("popup");
const openBtn = document.getElementById("openPopup");
const closeBtn = document.getElementById("close");

openBtn.addEventListener("click", () => {
    popup.style.display = "block";
});

closeBtn.addEventListener("click", () => {
    popup.style.display = "none";
});

window.addEventListener("click", (e) => {
  if (e.target === popup) {
    popup.style.display = "none";
  }
});
