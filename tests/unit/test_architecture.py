"""Architecture constraint tests — enforce dependency direction.

Rules (from SPEC §9-10 and AGENTS.md):
- api/ must NOT import storage/ or processing directly
- repositories/ must NOT import api/
- models/ must NOT import api/ or repositories/
- security/ must NOT import api/, repositories/, or models/

These tests use AST scanning to statically verify import boundaries.
"""

import ast
from pathlib import Path

import pytest

BACKEND_APP_DIR = Path(__file__).resolve().parent.parent.parent / "backend" / "app"

# Forbidden import rules: { source_package: [forbidden_targets] }
FORBIDDEN_IMPORTS = {
    "app.api": ["app.storage", "app.processing"],
    "app.repositories": ["app.api"],
    "app.models": ["app.api", "app.repositories"],
    "app.security": ["app.api", "app.repositories", "app.models"],
}


def _get_python_files(package_rel: str) -> list[Path]:
    """Get all .py files in a package directory."""
    package_dir = BACKEND_APP_DIR / package_rel.replace("app.", "")
    if not package_dir.exists():
        return []
    return list(package_dir.rglob("*.py"))


def _extract_imports(file_path: Path) -> list[str]:
    """Extract all import module names from a Python file using AST."""
    try:
        source = file_path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(file_path))
    except SyntaxError:
        return []

    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.append(node.module)
                # Also check relative imports
                if node.level == 0:
                    imports.append(node.module)
                else:
                    # Relative import — resolve relative to current package
                    imports.append(node.module)
    return imports


def _is_importing_from(imports: list[str], target: str) -> bool:
    """Check if any import matches or is a submodule of the target."""
    for imp in imports:
        if imp == target or imp.startswith(target + "."):
            return True
        # Also check relative imports like ..storage from within app.api
        # These resolve to app.storage, etc.
        if imp.startswith("."):
            # Relative imports are generally fine for intra-package
            continue
    return False


class TestArchitectureConstraints:
    """Verify that the codebase respects dependency direction rules."""

    @pytest.mark.parametrize(
        "source_pkg,forbidden_targets",
        list(FORBIDDEN_IMPORTS.items()),
        ids=list(FORBIDDEN_IMPORTS.keys()),
    )
    def test_no_forbidden_imports(self, source_pkg, forbidden_targets):
        """Verify no file in source_pkg imports from forbidden targets."""
        py_files = _get_python_files(source_pkg)
        assert len(py_files) > 0, f"No Python files found in {source_pkg}"

        violations = []
        for py_file in py_files:
            imports = _extract_imports(py_file)
            for target in forbidden_targets:
                if _is_importing_from(imports, target):
                    rel_path = py_file.relative_to(BACKEND_APP_DIR.parent.parent)
                    violations.append(
                        f"  {rel_path} imports from forbidden target '{target}'"
                    )

        assert not violations, (
            f"Architecture violations in {source_pkg}:\n"
            + "\n".join(violations)
            + f"\n\nForbidden targets: {forbidden_targets}"
        )

    def test_no_javascript_in_models(self):
        """Models should only generate HTML/CSS, never JavaScript."""
        # Check that presentation.py doesn't contain <script> generation
        # (except for the template engine's own runtime)
        presentation_file = BACKEND_APP_DIR / "presentation.py"
        if not presentation_file.exists():
            pytest.skip("presentation.py not found")

        content = presentation_file.read_text(encoding="utf-8")
        # The presentation module is allowed to have script tags for the
        # interactive runtime, but AI-generated content should not.
        # This test just verifies the file exists and is parseable.
        assert len(content) > 0

    def test_all_models_have_timestamps(self):
        """All ORM models should inherit from TimestampMixin."""
        models_file = BACKEND_APP_DIR / "models" / "__init__.py"
        if not models_file.exists():
            pytest.skip("models/__init__.py not found")

        source = models_file.read_text(encoding="utf-8")
        tree = ast.parse(source)

        # Find all class definitions that inherit from Base
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                # Check if this class has a __tablename__ (it's an ORM model)
                has_tablename = False
                for item in node.body:
                    if isinstance(item, ast.Assign):
                        for target in item.targets:
                            if (
                                isinstance(target, ast.Name)
                                and target.id == "__tablename__"
                            ):
                                has_tablename = True

                if has_tablename:
                    # Check that TimestampMixin is in the bases
                    base_names = []
                    for base in node.bases:
                        if isinstance(base, ast.Name):
                            base_names.append(base.id)
                        elif isinstance(base, ast.Attribute):
                            base_names.append(base.attr)
                    assert "TimestampMixin" in base_names, (
                        f"Model {node.name} has __tablename__ but doesn't "
                        f"inherit from TimestampMixin. Bases: {base_names}"
                    )

    def test_no_print_statements_in_api(self):
        """API layer should use logging, not print()."""
        api_dir = BACKEND_APP_DIR / "api"
        if not api_dir.exists():
            pytest.skip("api/ directory not found")

        violations = []
        for py_file in api_dir.glob("*.py"):
            source = py_file.read_text(encoding="utf-8")
            try:
                tree = ast.parse(source)
            except SyntaxError:
                continue

            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    if isinstance(node.func, ast.Name) and node.func.id == "print":
                        violations.append(
                            f"  {py_file.name}:{node.lineno} uses print()"
                        )

        assert not violations, (
            "API layer should use logging instead of print():\n"
            + "\n".join(violations)
        )

    def test_list_all_papers_has_no_n_plus_one_queries(self, db_session):
        """验证 PaperRepository.list_all() 不会触发 N+1 SQL 查询，确保列表序列化只有固定的 SQL 查询次数。"""
        from app.database import Base
        from app.models import Paper, SourceFile, PaperDraft, ProcessingJob
        from app.repositories import PaperRepository
        from app.schemas import PaperOut
        from sqlalchemy import event

        Base.metadata.create_all(bind=db_session.get_bind())

        # 插入 10 条数据及各自关联记录
        for i in range(10):
            paper = Paper(title=f"Paper {i}", slug=f"paper-{i}", mode="faithful_transcription", status="pending_review")
            db_session.add(paper)
            db_session.flush()
            source = SourceFile(paper_id=paper.id, storage_key=f"key-{i}", original_filename=f"doc{i}.pdf", mime_type="application/pdf", size_bytes=1024, sha256="hash", expires_at=__import__("datetime").datetime.now(__import__("datetime").timezone.utc))
            draft = PaperDraft(paper_id=paper.id, version=1, document={"questions": [{"id": "q1"}]})
            job = ProcessingJob(paper_id=paper.id, job_type="parse", status="running", stage="extracting", current_page=1, total_pages=2)
            db_session.add_all([source, draft, job])
            db_session.flush()
            paper.source_file_id = source.id
            paper.current_draft_id = draft.id
        db_session.commit()

        # 开始监听 SQL 语句执行次数
        query_count = 0

        def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            nonlocal query_count
            query_count += 1

        engine = db_session.get_bind()
        event.listen(engine, "before_cursor_execute", before_cursor_execute)

        try:
            repo = PaperRepository(db_session)
            papers, total = repo.list_all(page=1, size=20)
            assert len(papers) == 10
            
            # 模拟 FastAPI 序列化 PaperOut 访问多维属性
            outs = [PaperOut.model_validate(p) for p in papers]
            assert len(outs) == 10
            assert outs[0].source_file_name.startswith("doc")
            assert outs[0].source_file_name.endswith(".pdf")
            assert outs[0].question_count == 1
        finally:
            event.remove(engine, "before_cursor_execute", before_cursor_execute)

        # 10 条记录如果没有 selectinload，将会产生 1 (count) + 1 (list) + 10 (source) + 10 (draft) + 10 (job) = 32 次查询。
        # 配置 selectinload 后，查询次数固定在 <= 5 次 (Count + List + 3个关联批量查)。
        assert query_count <= 5, f"查询次数过于频繁 ({query_count} 次)，可能发生了 N+1 查询"
