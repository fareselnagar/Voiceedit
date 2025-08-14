
const fileInput = document.getElementById("fileInput");
const dropZone = document.getElementById("drop-zone");
const startBtn = document.getElementById("startBtn");
const presetSelect = document.getElementById("preset");
const progressWrap = document.getElementById("progress");
const prog = document.getElementById("prog");
const status = document.getElementById("status");
const preview = document.getElementById("preview");
const beforeAudio = document.getElementById("before");
const afterAudio = document.getElementById("after");
const downloadLink = document.getElementById("downloadLink");
let selectedFile = null;

dropZone.addEventListener("click", ()=> fileInput.click());
fileInput.addEventListener("change", (e) => {
  if (e.target.files.length) {
    selectedFile = e.target.files[0];
    beforeAudio.src = URL.createObjectURL(selectedFile);
  }
});

dropZone.addEventListener("dragover", (e)=>{ e.preventDefault(); dropZone.classList.add("hover"); });
dropZone.addEventListener("dragleave", (e)=>{ dropZone.classList.remove("hover"); });
dropZone.addEventListener("drop", (e)=> {
  e.preventDefault(); dropZone.classList.remove("hover");
  if (e.dataTransfer.files.length) {
    selectedFile = e.dataTransfer.files[0];
    beforeAudio.src = URL.createObjectURL(selectedFile);
  }
});

startBtn.addEventListener("click", ()=>{
  if (!selectedFile) {
    alert("اختر ملف صوتي أولاً");
    return;
  }
  uploadAndProcess(selectedFile);
});

function uploadAndProcess(file) {
  progressWrap.classList.remove("hidden");
  prog.value = 5;
  status.innerText = "جاري رفع الملف...";
  const fd = new FormData();
  fd.append("file", file);
  fd.append("preset", presetSelect.value);

  fetch("/process", { method:"POST", body: fd })
    .then(r => r.json())
    .then(data => {
      if (data.error) {
        status.innerText = "حدث خطأ: " + data.error;
        prog.value = 0;
        return;
      }
      status.innerText = "المعالجة اكتملت. تجهيز الملف...";
      prog.value = 90;
      const out = data.output;
      const url = "/download/" + out;
      afterAudio.src = url;
      downloadLink.href = url;
      downloadLink.innerText = "تحميل " + out;
      preview.classList.remove("hidden");
      prog.value = 100;
      status.innerText = "جاهز للتحميل والمعاينة";
    })
    .catch(err => {
      status.innerText = "خطأ في الاتصال: " + err;
      prog.value = 0;
    });
}
