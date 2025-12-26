(function () {
  function safeNumber(value, fallback) {
    var n = parseFloat(value);
    return isFinite(n) ? n : (fallback || 0);
  }

  function applyClinicalUserStatsToPage(stats) {
    if (!stats) return;

    var completedCasesEl = document.getElementById('completed-cases');
    if (completedCasesEl) completedCasesEl.textContent = stats.completed_cases != null ? stats.completed_cases : 0;

    var averageScoreEl = document.getElementById('average-score');
    if (averageScoreEl) {
      var completed = safeNumber(stats.completed_cases, 0);
      if (completed <= 0) {
        averageScoreEl.textContent = '-';
      } else {
        var avg = safeNumber(stats.average_score, 0);
        averageScoreEl.textContent = avg.toFixed(1) + '%';
      }
    }

    var progress = stats.difficulty_progress || {};
    ['beginner', 'intermediate', 'advanced'].forEach(function (level) {
      var levelProgress = progress[level];
      if (!levelProgress) return;

      var textEl = document.getElementById(level + '-progress');
      if (textEl) {
        textEl.textContent = (levelProgress.completed || 0) + '/' + (levelProgress.total || 0);
      }

      var barEl = document.getElementById(level + '-bar');
      if (barEl) {
        var total = safeNumber(levelProgress.total, 0);
        var completedN = safeNumber(levelProgress.completed, 0);
        var pct = total > 0 ? (completedN / total) * 100 : 0;
        barEl.style.width = pct + '%';
      }
    });

    // 可选：仪表板进度卡片（存在则更新）
    var totalCasesEl = document.getElementById('total-clinical-cases');
    if (totalCasesEl && stats.total_cases != null) totalCasesEl.textContent = stats.total_cases;

    var progressPctEl = document.getElementById('progress-percentage');
    if (progressPctEl && stats.progress_percentage != null) progressPctEl.textContent = stats.progress_percentage + '%';

    var studyTimeEl = document.getElementById('formatted-study-time');
    if (studyTimeEl && stats.formatted_study_time != null) studyTimeEl.textContent = stats.formatted_study_time;
  }

  function loadClinicalUserStats(onDone) {
    var url = '/api/clinical/user-stats/';

    if (window.jQuery && window.jQuery.ajax) {
      window.jQuery.ajax({
        url: url,
        method: 'GET',
        success: function (response) {
          if (response && response.success) {
            applyClinicalUserStatsToPage(response.data);
            if (typeof onDone === 'function') onDone(null, response.data);
          } else {
            if (typeof onDone === 'function') onDone(response || new Error('Invalid response'));
          }
        },
        error: function (xhr, status, error) {
          if (typeof onDone === 'function') onDone(error || status || xhr);
        }
      });
      return;
    }

    fetch(url, { credentials: 'same-origin' })
      .then(function (r) { return r.json(); })
      .then(function (response) {
        if (response && response.success) {
          applyClinicalUserStatsToPage(response.data);
          if (typeof onDone === 'function') onDone(null, response.data);
        } else {
          if (typeof onDone === 'function') onDone(response || new Error('Invalid response'));
        }
      })
      .catch(function (err) {
        if (typeof onDone === 'function') onDone(err);
      });
  }

  window.applyClinicalUserStatsToPage = applyClinicalUserStatsToPage;
  window.loadClinicalUserStats = loadClinicalUserStats;
})();
