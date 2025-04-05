document.querySelector('input[type="file"]').addEventListener('change', function() {

  const maxSize = 20 * 1024 * 1024; // 20MB in bytes
    const span_client = document.getElementById("client_error")
    const upload_btn_lib = document.getElementById("upload_btn_lib")


  if (this.files[0] && this.files[0].size > maxSize) {
        span_client.textContent = 'File size exceeds 20MB. Please select a smaller file.';
    this.value = ''; // Clear the input
      upload_btn_lib.disabled = true;
  }else{
      span_client.textContent = '';
      upload_btn_lib.disabled = false;

  }
});