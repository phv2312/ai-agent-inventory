function run() {
  const chatTab = document.getElementById("chat-tab");
  if (!chatTab) return;

  const tabsContainer = chatTab.parentNode;
  const tabNav =
    tabsContainer?.querySelector(".tab-nav") ||
    tabsContainer?.firstElementChild;

  if (tabNav) {
    tabNav.classList.add("header-bar");
  }

  if (tabsContainer) {
    tabsContainer.style.padding = "0";
    tabsContainer.style.margin = "0";
    tabsContainer.style.border = "none";
    tabsContainer.style.boxShadow = "none";
    if (tabsContainer.parentNode) {
      tabsContainer.parentNode.style.gap = "0";
      if (tabsContainer.parentNode.parentNode) {
        tabsContainer.parentNode.parentNode.style.padding = "0";
      }
    }
  }

  const convDropdown = document.querySelector(
    "#conversation-dropdown input",
  );
  if (convDropdown) {
    convDropdown.placeholder = "Browse conversation";
  }

  const infoExpandButton = document.getElementById("info-expand-button");
  const chatInfoPanel = document.getElementById("info-expand");
  if (infoExpandButton && chatInfoPanel) {
    const summary = chatInfoPanel.querySelector("summary, .label-wrap");
    if (summary) {
      summary.appendChild(infoExpandButton);
    } else if (chatInfoPanel.childNodes[2]) {
      chatInfoPanel.insertBefore(
        infoExpandButton,
        chatInfoPanel.childNodes[2],
      );
    }
  }

  const convColumn = document.getElementById("conv-settings-panel");
  const defaultConvColumnMinWidth = "min(300px, 100%)";

  if (convColumn) {
    convColumn.style.minWidth = defaultConvColumnMinWidth;
  }

  globalThis.scrollToChunk = (chunkId) => {
    const target = document.getElementById(`chunk-${chunkId}`);
    if (!target) return;
    target.open = true;
    const mark = target.querySelector("mark");
    if (mark) {
      mark.scrollIntoView({ behavior: "smooth", block: "center" });
    } else {
      target.scrollIntoView({ behavior: "smooth", block: "start" });
    }
    target.classList.add("chunk-highlight");
    setTimeout(() => target.classList.remove("chunk-highlight"), 2000);
  };

  globalThis.toggleChatColumn = () => {
    if (!convColumn) return;
    const flexGrow = convColumn.style.flexGrow;
    if (flexGrow === "0") {
      convColumn.style.flexGrow = "1";
      convColumn.style.minWidth = defaultConvColumnMinWidth;
    } else {
      convColumn.style.flexGrow = "0";
      convColumn.style.minWidth = "0px";
    }
  };

  const MSG_SET = "kn-inline-set";

  globalThis.knUpdateWidget = (data) => {
    if (!data || data.visible === false) {
      return;
    }

    const titleEl = document.getElementById("kn-widget-title");
    if (titleEl && data.title) {
      titleEl.textContent = data.title;
      titleEl.style.display = "";
    }

    const iframe = document.getElementById("kn-widget-iframe");
    if (!iframe) {
      return;
    }

    const postMarkup = () => {
      iframe.contentWindow?.postMessage(
        { type: MSG_SET, html: data.html || "" },
        "*",
      );
    };

    if (data.done && data.srcdoc) {
      iframe.srcdoc = data.srcdoc;
      return;
    }

    if (data.html == null) {
      return;
    }

    if (iframe.contentDocument?.readyState === "complete") {
      postMarkup();
    } else {
      iframe.addEventListener("load", postMarkup, { once: true });
    }
  };

  // ── Widget fullscreen (event delegation — gr.HTML blocks inline <script>) ──
  document.addEventListener("click", (e) => {
    if (e.target.closest(".kn-fs-btn")) {
      const block = e.target.closest(".info-widget-block");
      const overlay = block?.querySelector(".kn-fs-overlay");
      if (overlay) {
        overlay.style.display = "flex";
        document.body.style.overflow = "hidden";
      }
    } else if (e.target.closest(".kn-fs-close")) {
      const overlay = e.target.closest(".kn-fs-overlay");
      if (overlay) {
        overlay.style.display = "none";
        document.body.style.overflow = "";
      }
    } else if (e.target.classList.contains("kn-fs-overlay")) {
      e.target.style.display = "none";
      document.body.style.overflow = "";
    }
  });
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") {
      document.querySelectorAll(".kn-fs-overlay").forEach((o) => {
        o.style.display = "none";
      });
      document.body.style.overflow = "";
    }
  });

  // Apply saved theme or default to dark
  const savedTheme = localStorage.getItem("theme") || "dark";
  if (savedTheme === "dark") {
    document.body.classList.add("dark");
  } else {
    document.body.classList.remove("dark");
  }

  // Inject version badge + dark/light toggle into the tab nav bar
  if (tabNav) {
    const toggleBtn = document.createElement("button");
    toggleBtn.id = "theme-toggle-btn";
    toggleBtn.title = "Toggle dark / light mode";
    toggleBtn.innerHTML = `<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="currentColor"><path d="M12 22C17.5228 22 22 17.5228 22 12C22 6.47715 17.5228 2 12 2C6.47715 2 2 6.47715 2 12C2 17.5228 6.47715 22 12 22ZM12 20.5V3.5C16.6944 3.5 20.5 7.30558 20.5 12C20.5 16.6944 16.6944 20.5 12 20.5Z"/></svg>`;
    toggleBtn.onclick = () => {
      const isDark = document.body.classList.toggle("dark");
      localStorage.setItem("theme", isDark ? "dark" : "light");
    };
    tabNav.appendChild(toggleBtn);
  }
}
