{ pkgs ? import <nixpkgs> {} }:

pkgs.mkShell {
  name = "python-pytest-env";

  buildInputs = with pkgs; [
    python312
    python312Packages.pip
    python312Packages.virtualenv
    python312Packages.pytest
    python312Packages.pytest-asyncio
  ];

  shellHook = ''
    echo "шелл активирован"

    export PYTHONPATH=$(pwd)/lab01/backend

    if [ ! -d ".venv" ]; then
      python -m venv .venv
    fi

    source .venv/bin/activate

    if [ -f "lab01/backend/requirements.txt" ]; then
      pip install -r lab01/backend/requirements.txt
    fi

    echo "все команды в мейкфайле:"
    echo "make lab01-up"
    echo "make lab01-tests"
    echo "make lab01-tests-invariant"
  '';
}