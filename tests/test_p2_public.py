"""端到端公网测试 - 验证 P2 修复"""
import requests
import json
import time

BASE_URL = "https://tpaper.tpgofighting.top"
ADMIN_USER = "admin"
ADMIN_PASS = "rkiOqvL2WR7Uwlw0"

class TestResult:
    def __init__(self, name, passed, message=""):
        self.name = name
        self.passed = passed
        self.message = message

def login(session):
    """登录获取 session cookie"""
    resp = session.post(
        f"{BASE_URL}/api/auth/login",
        json={"username": ADMIN_USER, "password": ADMIN_PASS},
        headers={"X-Requested-With": "XMLHttpRequest"}
    )
    return resp.status_code == 200

def test_pagination(session):
    """测试分页功能"""
    results = []
    
    # 测试默认分页
    resp = session.get(f"{BASE_URL}/api/papers")
    if resp.status_code == 200:
        results.append(TestResult("GET /api/papers 默认分页", True))
    else:
        results.append(TestResult("GET /api/papers 默认分页", False, f"状态码: {resp.status_code}"))
    
    # 测试带分页参数
    resp = session.get(f"{BASE_URL}/api/papers?page=1&size=5")
    if resp.status_code == 200:
        data = resp.json()
        if isinstance(data, list):
            results.append(TestResult("GET /api/papers?page=1&size=5 分页参数", True))
        else:
            results.append(TestResult("GET /api/papers?page=1&size=5 分页参数", False, "返回格式错误"))
    else:
        results.append(TestResult("GET /api/papers?page=1&size=5 分页参数", False, f"状态码: {resp.status_code}"))
    
    # 测试搜索
    resp = session.get(f"{BASE_URL}/api/papers?q=test")
    if resp.status_code == 200:
        results.append(TestResult("GET /api/papers?q=test 搜索", True))
    else:
        results.append(TestResult("GET /api/papers?q=test 搜索", False, f"状态码: {resp.status_code}"))
    
    return results

def test_paper_crud(session):
    """测试 Paper CRUD"""
    results = []
    
    # 创建 Paper
    resp = session.post(
        f"{BASE_URL}/api/papers",
        json={"title": "测试试卷 P2", "mode": "faithful_transcription"},
        headers={"X-Requested-With": "XMLHttpRequest"}
    )
    if resp.status_code == 201:
        paper = resp.json()
        paper_id = paper["id"]
        results.append(TestResult("POST /api/papers 创建", True, f"paper_id={paper_id}"))
    else:
        results.append(TestResult("POST /api/papers 创建", False, f"状态码: {resp.status_code}"))
        return results
    
    # 获取单个 Paper
    resp = session.get(f"{BASE_URL}/api/papers/{paper_id}")
    if resp.status_code == 200:
        results.append(TestResult(f"GET /api/papers/{paper_id} 获取", True))
    else:
        results.append(TestResult(f"GET /api/papers/{paper_id} 获取", False, f"状态码: {resp.status_code}"))
    
    # 删除 Paper (测试 cascade)
    resp = session.delete(
        f"{BASE_URL}/api/papers/{paper_id}",
        headers={"X-Requested-With": "XMLHttpRequest"}
    )
    if resp.status_code == 204:
        results.append(TestResult(f"DELETE /api/papers/{paper_id} 删除 (cascade)", True))
    else:
        results.append(TestResult(f"DELETE /api/papers/{paper_id} 删除 (cascade)", False, f"状态码: {resp.status_code}"))
    
    # 验证删除
    resp = session.get(f"{BASE_URL}/api/papers/{paper_id}")
    if resp.status_code == 404:
        results.append(TestResult(f"GET /api/papers/{paper_id} 验证删除", True))
    else:
        results.append(TestResult(f"GET /api/papers/{paper_id} 验证删除", False, f"状态码: {resp.status_code}"))
    
    return results

def test_jobs(session):
    """测试 Jobs API"""
    results = []
    
    # 获取 Jobs 列表
    resp = session.get(f"{BASE_URL}/api/jobs/paper/1")
    if resp.status_code == 200:
        results.append(TestResult("GET /api/jobs/paper/1", True))
    else:
        results.append(TestResult("GET /api/jobs/paper/1", False, f"状态码: {resp.status_code}"))
    
    return results

def test_health(session):
    """测试健康检查"""
    results = []
    
    resp = session.get(f"{BASE_URL}/health")
    if resp.status_code == 200:
        results.append(TestResult("GET /health", True))
    else:
        results.append(TestResult("GET /health", False, f"状态码: {resp.status_code}"))
    
    return results

def main():
    print("=" * 60)
    print("TPaper 端到端公网测试 - P2 修复验证")
    print("=" * 60)
    
    session = requests.Session()
    
    # 登录
    print("\n[1] 登录...")
    if login(session):
        print("    ✓ 登录成功")
    else:
        print("    ✗ 登录失败")
        return
    
    # 健康检查
    print("\n[2] 健康检查...")
    results = test_health(session)
    for r in results:
        status = "✓" if r.passed else "✗"
        print(f"    {status} {r.name}")
    
    # 分页测试
    print("\n[3] 分页功能测试...")
    results = test_pagination(session)
    for r in results:
        status = "✓" if r.passed else "✗"
        print(f"    {status} {r.name}")
    
    # CRUD 测试
    print("\n[4] Paper CRUD 测试...")
    results = test_paper_crud(session)
    for r in results:
        status = "✓" if r.passed else "✗"
        print(f"    {status} {r.name}")
    
    # Jobs 测试
    print("\n[5] Jobs API 测试...")
    results = test_jobs(session)
    for r in results:
        status = "✓" if r.passed else "✗"
        print(f"    {status} {r.name}")
    
    print("\n" + "=" * 60)
    print("测试完成!")
    print("=" * 60)

if __name__ == "__main__":
    main()
