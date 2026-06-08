document.addEventListener("DOMContentLoaded", () => {
  document.body.addEventListener("htmx:afterSwap", (event) => {
    if (event.target && event.target.id === "property-map") {
      window.dispatchEvent(new Event("marketplace:map-ready"));
    }
  });
});

