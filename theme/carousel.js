/* The photo carousel on the Gallery page, as on the old site: one large
   photo with its caption, arrows either side, and a strip of thumbnails
   underneath. It is built from the page's ordinary photo grid (a
   <div class="gallery carousel"> of <figure>s), so without JavaScript the
   grid simply stays as it is.

   Arrow buttons, the arrow keys, a click on a thumbnail, or a swipe on a
   phone move between photos. */
(function () {
  "use strict";

  function build(grid) {
    var photos = Array.prototype.map.call(grid.querySelectorAll("figure"), function (fig) {
      var img = fig.querySelector("img"), cap = fig.querySelector("figcaption");
      return { src: img.getAttribute("src"), alt: img.getAttribute("alt") || "",
               caption: cap ? cap.innerHTML : "" };
    });
    if (photos.length < 2) return;

    var root = document.createElement("div");
    root.className = "carousel-view";
    root.setAttribute("role", "region");
    root.setAttribute("aria-roledescription", "carousel");
    root.setAttribute("aria-label", "Photo gallery");
    root.tabIndex = 0;
    root.innerHTML =
      '<div class="carousel-stage">' +
      '  <div class="carousel-track"></div>' +
      '  <button class="carousel-prev" type="button" aria-label="Previous photo">&#8249;</button>' +
      '  <button class="carousel-next" type="button" aria-label="Next photo">&#8250;</button>' +
      '</div>' +
      '<p class="carousel-count" aria-live="polite"></p>' +
      '<div class="carousel-thumbs"></div>';

    var stage = root.querySelector(".carousel-stage"),
        track = root.querySelector(".carousel-track"),
        thumbs = root.querySelector(".carousel-thumbs"),
        count = root.querySelector(".carousel-count");

    photos.forEach(function (p, i) {
      var slide = document.createElement("figure");
      slide.className = "carousel-slide";
      slide.setAttribute("aria-hidden", "true");
      slide.innerHTML = '<div class="carousel-frame"><img alt="" loading="lazy">' +
        (p.caption ? "<figcaption>" + p.caption + "</figcaption>" : "") + "</div>";
      var img = slide.querySelector("img");
      img.src = p.src;
      img.alt = p.alt;
      track.appendChild(slide);

      var t = document.createElement("button");
      t.type = "button";
      t.className = "carousel-thumb";
      t.setAttribute("aria-label", "Photo " + (i + 1) + (p.alt ? ": " + p.alt : ""));
      t.innerHTML = '<img alt="" loading="lazy">';
      t.querySelector("img").src = p.src;
      t.addEventListener("click", function () { show(i); });
      thumbs.appendChild(t);
    });

    var slides = track.children, buttons = thumbs.children, current = -1;

    function show(i) {
      i = (i + photos.length) % photos.length;   // wrap around at either end
      if (i === current) return;
      if (current >= 0) {
        slides[current].setAttribute("aria-hidden", "true");
        buttons[current].classList.remove("active");
        buttons[current].removeAttribute("aria-current");
      }
      current = i;
      stage.scrollLeft = 0;                     // older browsers without overflow: clip
      track.style.transform = "translateX(" + (-100 * i) + "%)";
      slides[i].removeAttribute("aria-hidden");
      buttons[i].classList.add("active");
      buttons[i].setAttribute("aria-current", "true");
      count.textContent = (i + 1) + " / " + photos.length;
      [i - 1, i, i + 1].forEach(function (n) {   // fetch neighbours ahead of time
        var img = slides[(n + photos.length) % photos.length].querySelector("img");
        img.loading = "eager";
      });
      var b = buttons[i];                       // keep the thumbnail in view
      thumbs.scrollTo({ left: b.offsetLeft - (thumbs.clientWidth - b.offsetWidth) / 2,
                        behavior: "smooth" });
    }

    root.querySelector(".carousel-prev").addEventListener("click", function () { show(current - 1); });
    root.querySelector(".carousel-next").addEventListener("click", function () { show(current + 1); });
    root.addEventListener("keydown", function (e) {
      if (e.key === "ArrowLeft") { show(current - 1); e.preventDefault(); }
      if (e.key === "ArrowRight") { show(current + 1); e.preventDefault(); }
    });

    var startX = null;                          // swipe on touch screens
    track.addEventListener("touchstart", function (e) { startX = e.touches[0].clientX; }, { passive: true });
    track.addEventListener("touchend", function (e) {
      if (startX === null) return;
      var dx = e.changedTouches[0].clientX - startX;
      if (Math.abs(dx) > 40) show(current + (dx < 0 ? 1 : -1));
      startX = null;
    });

    grid.parentNode.replaceChild(root, grid);
    show(0);
  }

  document.querySelectorAll(".gallery.carousel").forEach(build);
})();
