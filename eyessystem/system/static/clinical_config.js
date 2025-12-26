(function () {
  'use strict';

  // 全局临床推理页面配置常量（可在此文件持续扩展）
  // 约定：页面代码只读这些值，不在运行时随意修改
  window.CLINICAL_CONFIG = Object.assign({}, window.CLINICAL_CONFIG, {
    // 病史采集：进入下一阶段前，建议至少问多少个问题
    MIN_HISTORY_QUESTIONS: 3,

    // 病史采集：右侧问诊进度条以多少个问题作为“满值”参考
    HISTORY_PROGRESS_TARGET_QUESTIONS: 8,

    // 治疗阶段：治疗依据最少字符数（用于前端提交校验）
    TREATMENT_RATIONALE_MIN_CHARS: 20
  });
})();
