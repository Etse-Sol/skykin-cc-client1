(function () {
  ["skykinBlCard", "skykinBlNum", "skykinBlReason", "skykinBlAdd"].forEach(function (id) {
    var el = document.getElementById(id);
    if (el && el.parentNode) el.parentNode.removeChild(el);
  });
})();
