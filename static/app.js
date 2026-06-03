let deferredInstallPrompt = null;

function registerServiceWorker() {
  if (!("serviceWorker" in navigator)) {
    return;
  }

  window.addEventListener("load", () => {
    navigator.serviceWorker.register("/service-worker.js").catch(() => undefined);
  });
}

function setupInstallButton() {
  const installButton = document.querySelector("[data-install-app]");
  if (!installButton) {
    return;
  }

  const showButton = () => {
    installButton.hidden = false;
  };

  window.addEventListener("beforeinstallprompt", (event) => {
    event.preventDefault();
    deferredInstallPrompt = event;
    showButton();
  });

  installButton.addEventListener("click", async () => {
    if (!deferredInstallPrompt) {
      alert("如果浏览器支持，可以在地址栏菜单里选择“安装应用”或“添加到桌面”。");
      return;
    }

    deferredInstallPrompt.prompt();
    await deferredInstallPrompt.userChoice.catch(() => undefined);
    deferredInstallPrompt = null;
    installButton.hidden = true;
  });

  window.addEventListener("appinstalled", () => {
    deferredInstallPrompt = null;
    installButton.hidden = true;
  });
}

registerServiceWorker();
setupInstallButton();
