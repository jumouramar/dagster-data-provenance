import ast
import hashlib
import importlib.metadata
import inspect
import os
import subprocess
import sys
import settings

IGNORE_DIRS = {".git", "__pycache__", ".venv", "venv", "env", ".dagster", "storage", "logs"}


# --- Captura de ambiente ---

def git_hash() -> str | None:
    """Retorna o hash do commit atual. Tenta git CLI, depois lê .git/HEAD direto."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    try:
        git_head = os.path.join(os.getcwd(), ".git", "HEAD")
        if os.path.isfile(git_head):
            with open(git_head, "r", encoding="utf-8") as f:
                content = f.read().strip()
            if content.startswith("ref:"):
                ref = content.split(":", 1)[1].strip()
                ref_path = os.path.join(os.getcwd(), ".git", *ref.split("/"))
                if os.path.isfile(ref_path):
                    with open(ref_path, "r", encoding="utf-8") as rf:
                        return rf.read().strip()
            else:
                return content
    except Exception:
        pass
    return None


def installed_packages() -> dict[str, str | None]:
    """Escaneia arquivos .py do repositório e retorna {pacote: versão} dos imports."""
    base_dir = os.getcwd()
    stdlib_modules = set(getattr(sys, "stdlib_module_names", ()))
    imported_modules: set[str] = set()

    for root, dirs, files in os.walk(base_dir):
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
        for fn in files:
            if not fn.endswith(".py"):
                continue
            path = os.path.join(root, fn)
            try:
                with open(path, "r", encoding="utf-8") as f:
                    tree = ast.parse(f.read(), filename=path)
            except Exception:
                continue
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imported_modules.add(alias.name.split(".", 1)[0])
                elif isinstance(node, ast.ImportFrom):
                    if node.level and node.module is None:
                        continue
                    if node.module:
                        imported_modules.add(node.module.split(".", 1)[0])

    deps: dict[str, str | None] = {}
    module_to_distributions = importlib.metadata.packages_distributions()
    for module_name in sorted(imported_modules):
        if not module_name or module_name in stdlib_modules:
            continue
        distributions = module_to_distributions.get(module_name)
        if distributions:
            for dist_name in distributions:
                try:
                    deps[dist_name] = importlib.metadata.version(dist_name)
                except Exception:
                    deps.setdefault(dist_name, None)
        else:
            try:
                deps[module_name] = importlib.metadata.version(module_name)
            except Exception:
                pass

    if deps:
        return deps
    return {
        dist.metadata["Name"]: dist.metadata.get("Version")
        for dist in importlib.metadata.distributions()
        if dist.metadata.get("Name")
    }


def definition_hash() -> str | None:
    """Hash SHA1 de todos os arquivos .py do repositório — detecta mudanças no código."""
    try:
        base = os.getcwd()
        h = hashlib.sha1()
        for root, dirs, files in os.walk(base):
            dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
            for fn in sorted(files):
                if not fn.endswith(".py"):
                    continue
                try:
                    with open(os.path.join(root, fn), "rb") as f:
                        h.update(f.read())
                except Exception:
                    pass
        return h.hexdigest()
    except Exception:
        return None


# --- Inspeção de assets Dagster ---

def get_asset_source(op_or_assets_def) -> str | None:
    """Extrai código-fonte de uma AssetsDefinition (sensor) ou op_def (IOManager)."""
    op = getattr(op_or_assets_def, "op", op_or_assets_def)
    try:
        return inspect.getsource(op.compute_fn.decorated_fn)
    except Exception:
        pass
    try:
        return inspect.getsource(op.compute_fn)
    except Exception:
        return None


def get_asset_upstreams(op_def) -> list[str]:
    """Retorna nomes dos parâmetros upstream de um op_def (exclui 'context')."""
    try:
        sig = inspect.signature(op_def.compute_fn.decorated_fn)
        return [p for p in sig.parameters if p != "context"]
    except Exception:
        return []


# --- Helpers e factories ---

def filter_secrets(obj):
    """Remove chaves sensíveis (password, secret, token, key, cred) de dicts recursivamente."""
    if isinstance(obj, dict):
        return {
            k: filter_secrets(v)
            for k, v in obj.items()
            if not any(s in k.lower() for s in ("pass", "secret", "token", "key", "cred"))
        }
    if isinstance(obj, list):
        return [filter_secrets(x) for x in obj]
    return obj


def make_provenance_resource():
    from core_provenance.resources.provenance import ProvenanceResource  # noqa: PLC0415

    return ProvenanceResource(
        host=settings.POSTGRES_HOST,
        port=settings.POSTGRES_PORT,
        dbname=settings.POSTGRES_DB,
        user=settings.POSTGRES_USER,
        password=settings.POSTGRES_PASSWORD,
        environment=settings.ENVIRONMENT,
    )


def make_provenance_io_manager():
    from core_provenance.resources.provenance_io_manager import ProvenanceIOManager  # noqa: PLC0415

    return ProvenanceIOManager(
        host=settings.POSTGRES_HOST,
        port=settings.POSTGRES_PORT,
        dbname=settings.POSTGRES_DB,
        user=settings.POSTGRES_USER,
        password=settings.POSTGRES_PASSWORD,
        environment=settings.ENVIRONMENT,
    )
