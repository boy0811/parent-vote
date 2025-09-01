{% extends "layout.html" %}
{% block title %}候選人晉級處理{% endblock %}

{% block content %}
<div class="container mt-5">
  <div class="text-center mb-4">
    <h2>🏆 候選人晉級處理</h2>
    <p class="text-muted">從已結束的投票階段中選出晉級者</p>
  </div>

  <!-- ✅ 階段下拉選單 -->
  <form method="get" action="{{ url_for('admin_promote.promote_page') }}" class="mb-4 text-center">
    <div class="form-group d-flex justify-content-center align-items-center gap-2 flex-wrap">
      <label for="phase_id" class="form-label fw-bold">📌 選擇階段：</label>
      <select name="phase_id" id="phase_id" class="form-select w-auto" onchange="this.form.submit()">
        {% for phase in phases %}
          <option value="{{ phase.id }}" {% if current_phase and phase.id == current_phase.id %}selected{% endif %}>
            {{ phase.name }}
          </option>
        {% endfor %}
      </select>
    </div>
  </form>

  <!-- ✅ 晉級統計說明 -->
  <div class="alert alert-info text-center">
    預計晉級：<strong>{{ promote_count }}</strong> 人，
    自動晉級：<strong>{{ auto_promoted|length }}</strong> 人，
    同票待選：<strong>{{ tied_candidates|length }}</strong> 人，
    尚需勾選：<strong>{{ remaining_to_promote }}</strong> 人
  </div>

  {% if tied_candidates %}
  <form method="POST" action="{{ url_for('admin_promote.save_promoted_candidates') }}">
    <input type="hidden" name="phase_id" value="{{ current_phase.id }}">

    <div class="text-center mb-2">
      <p class="text-danger fw-bold">請從下列同票者中勾選 <strong>{{ remaining_to_promote }}</strong> 人晉級</p>
      <p id="selectedCountText" class="text-primary">已選 0 / {{ remaining_to_promote }} 人</p>
    </div>

    <div class="row justify-content-center">
      {% for item in tied_candidates %}
      <div class="col-md-4 col-sm-6 mb-3">
        <div class="form-check border p-3 rounded">
          <input type="checkbox" name="candidate_ids" value="{{ item[0].id }}" class="form-check-input checkbox-candidate" id="checkbox-{{ item[0].id }}">
          <label class="form-check-label" for="checkbox-{{ item[0].id }}">
            {{ item[0].class_name }} - {{ item[0].parent_name }}（{{ item[1] }} 票）
          </label>
        </div>
      </div>
      {% endfor %}
    </div>

    <div class="text-center mt-3">
      <button type="submit" class="btn btn-success">✅ 儲存晉級名單</button>
    </div>
  </form>
  {% else %}
    <div class="alert alert-success text-center">
      🎉 已自動完成晉級處理！
    </div>
  {% endif %}

  <!-- 🔍 晉級名單 -->
  <div class="mt-5">
    <h5>📋 本階段晉級名單（共 {{ actual_promoted_count }} 人）：</h5>
    <ul class="list-group mt-2">
      {% for item in auto_promoted %}
        <li class="list-group-item">
          {{ item[0].class_name }} - {{ item[0].parent_name }}（{{ item[1] }} 票）
        </li>
      {% endfor %}
    </ul>
  </div>
</div>

<script>
// ✅ 即時更新勾選人數
document.addEventListener("DOMContentLoaded", function () {
  const checkboxes = document.querySelectorAll(".checkbox-candidate");
  const countText = document.getElementById("selectedCountText");
  const maxCount = {{ remaining_to_promote }};

  function updateCount() {
    const selectedCount = Array.from(checkboxes).filter(cb => cb.checked).length;
    countText.innerText = `已選 ${selectedCount} / ${maxCount} 人`;

    // 超過就禁止勾選
    checkboxes.forEach(cb => {
      if (!cb.checked && selectedCount >= maxCount) {
        cb.disabled = true;
      } else {
        cb.disabled = false;
      }
    });
  }

  checkboxes.forEach(cb => cb.addEventListener("change", updateCount));
});
</script>
{% endblock %}
