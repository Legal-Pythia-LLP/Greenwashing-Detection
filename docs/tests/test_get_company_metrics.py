from app.core.tools import WikirateClient
from app.config import WIKIRATE_API_KEY
import json
import os

def test_get_company_metrics():
    """测试获取公司ESG指标数据的功能"""
    
    # 初始化客户端
    wikirate_client = WikirateClient(WIKIRATE_API_KEY)
    
    # 测试公司列表
    test_companies = ["Apple Inc", "Puma", "HSBC", "KPMG UNITED KINGDOM PLC"]
    
    # 存储所有测试结果
    all_results = {}
    
    for company_name in test_companies:
        print(f"\n{'='*60}")
        print(f"测试公司: {company_name}")
        print(f"{'='*60}")
        
        try:
            # 获取公司ESG指标数据
            results = wikirate_client.get_company_metrics(company_name)
            
            # 存储结果
            all_results[company_name] = results
            
            # 检查返回结果
            if "error" in results:
                print(f"❌ 错误: {results['error']}")
                continue
            
            # 打印基本信息
            print(f"✅ 公司名称: {results.get('company_name')}")
            print(f"📊 总答案数: {results.get('total_answers')}")
            print(f"🌱 ESG指标数量: {results.get('esg_metrics_count')}")
            
            # 打印ESG数据详情
            esg_data = results.get('esg_data', [])
            if esg_data:
                print(f"\n📋 ESG数据详情 (前5条):")
                for i, record in enumerate(esg_data[:5], 1):
                    print(f"  {i}. 指标: {record.get('metric_name')}")
                    print(f"     年份: {record.get('year')}")
                    print(f"     数值: {record.get('value')}")
                    print(f"     主题: {record.get('topics')}")
                    comments = record.get('comments')
                    if comments:
                        print(f"     备注: {comments[:100]}...")
                    else:
                        print(f"     备注: 无")
                    print()
            else:
                print("⚠️  没有找到ESG相关数据")
            
            # 保存单个公司结果到JSON文件
            filename = f"test_results_{company_name.replace(' ', '_')}.json"
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
            print(f"💾 结果已保存到: {filename}")
            
        except Exception as e:
            print(f"❌ 测试失败: {e}")
            all_results[company_name] = {"error": str(e)}
            continue
    
    # 保存所有结果到同名文件
    current_file = os.path.basename(__file__)
    json_filename = current_file.replace('.py', '.json')
    
    with open(json_filename, 'w', encoding='utf-8') as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)
    
    print(f"\n💾 所有测试结果已保存到: {json_filename}")
    return all_results

def test_single_company():
    """测试单个公司的详细数据"""
    
    wikirate_client = WikirateClient(WIKIRATE_API_KEY)
    company_name = "Apple Inc"
    
    print(f"\n{'='*60}")
    print(f"详细测试: {company_name}")
    print(f"{'='*60}")
    
    results = wikirate_client.get_company_metrics(company_name)
    
    if "error" not in results:
        print(f"✅ 成功获取数据")
        print(f"📊 总答案数: {results.get('total_answers')}")
        print(f"🌱 ESG指标数: {results.get('esg_metrics_count')}")
        
        # 按主题分类显示
        esg_data = results.get('esg_data', [])
        topics_count = {}
        for record in esg_data:
            topics = record.get('topics', [])
            for topic in topics:
                topics_count[topic] = topics_count.get(topic, 0) + 1
        
        print(f"\n📈 主题分布:")
        for topic, count in topics_count.items():
            print(f"  {topic}: {count}条")
        
        # 显示所有ESG数据
        print(f"\n📋 所有ESG数据:")
        for i, record in enumerate(esg_data, 1):
            print(f"{i:2d}. {record.get('metric_name')} ({record.get('year')}) = {record.get('value')}")
    else:
        print(f"❌ 错误: {results['error']}")

if __name__ == "__main__":
    print("开始测试 get_company_metrics 函数...")
    
    # 运行基本测试
    all_results = test_get_company_metrics()
    
    # 运行详细测试
    test_single_company()
    
    print("\n测试完成!") 