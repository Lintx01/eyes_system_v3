"""检查诊断选项数据"""
import django
import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'eyehospital.settings')
django.setup()

from cases.models import ClinicalCase, DiagnosisOption

# 检查案例
case_id = 'CCC7D361F8'
try:
    case = ClinicalCase.objects.get(case_id=case_id)
    print(f"✓ 案例找到: {case.title}")
    
    # 检查诊断选项
    diagnosis_options = DiagnosisOption.objects.filter(clinical_case=case)
    print(f"\n诊断选项数量: {diagnosis_options.count()}")
    
    correct_diagnoses = diagnosis_options.filter(is_correct_diagnosis=True)
    print(f"正确诊断数量: {correct_diagnoses.count()}")
    
    for opt in diagnosis_options:
        marker = "✓" if opt.is_correct_diagnosis else " "
        print(f"\n{marker} 诊断名称: {opt.diagnosis_name}")
        print(f"  是否正确: {opt.is_correct_diagnosis}")
        print(f"  显示顺序: {opt.display_order}")
        print(f"  难度级别: {opt.difficulty_level}")
        
    if diagnosis_options.count() == 0:
        print("\n⚠ 警告: 该案例没有诊断选项！需要创建诊断选项。")
        
        # 检查其他案例是否有诊断选项
        all_diagnoses = DiagnosisOption.objects.all()
        print(f"\n数据库中总诊断选项数: {all_diagnoses.count()}")
        
        if all_diagnoses.count() > 0:
            print("\n其他案例的诊断选项示例:")
            for diag in all_diagnoses[:5]:
                print(f"  - {diag.diagnosis_name} ({diag.clinical_case.case_id})")
        
except ClinicalCase.DoesNotExist:
    print(f"✗ 错误: 案例 {case_id} 不存在")
