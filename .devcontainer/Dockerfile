FROM ubuntu:22.04

# 基本設定
ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=Asia/Tokyo

# パッケージリストの更新とロケール設定
RUN apt-get update && apt-get install -y \
    locales \
    tzdata \
    && locale-gen ja_JP.UTF-8 \
    && update-locale LANG=ja_JP.UTF-8 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# 環境変数設定
ENV LANG=ja_JP.UTF-8
ENV LANGUAGE=ja_JP:ja
ENV LC_ALL=ja_JP.UTF-8

# 基本開発ツールのインストール
RUN apt-get update && apt-get install -y \
    # 基本ツール
    curl \
    wget \
    unzip \
    git \
    vim \
    nano \
    make \
    build-essential \
    # zsh関連
    zsh \
    zsh-autosuggestions \
    zsh-syntax-highlighting \
    # その他便利ツール
    tree \
    htop \
    jq \
    sqlite3 \
    ca-certificates \
    gnupg \
    lsb-release \
    software-properties-common \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# JUSTタスクランナーのインストール
RUN JUST_VERSION=$(curl -s https://api.github.com/repos/casey/just/releases/latest | grep '"tag_name"' | sed -E 's/.*"([^"]+)".*/\1/') \
    && ARCH=$(uname -m) \
    && curl -L "https://github.com/casey/just/releases/download/${JUST_VERSION}/just-${JUST_VERSION}-${ARCH}-unknown-linux-musl.tar.gz" -o just.tar.gz \
    && tar -xzf just.tar.gz \
    && mv just /usr/local/bin/just \
    && chmod +x /usr/local/bin/just \
    && rm just.tar.gz

# oh-my-zshのインストール
RUN sh -c "$(curl -fsSL https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh)" "" --unattended

# root以外のユーザー作成
ARG USERNAME=developer
ARG USER_UID=1000
ARG USER_GID=$USER_UID

RUN groupadd --gid $USER_GID $USERNAME \
    && useradd --uid $USER_UID --gid $USER_GID -m $USERNAME -s /bin/zsh \
    && apt-get update \
    && apt-get install -y sudo \
    && echo $USERNAME ALL=\(root\) NOPASSWD:ALL > /etc/sudoers.d/$USERNAME \
    && chmod 0440 /etc/sudoers.d/$USERNAME \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# ユーザー切り替え
USER $USERNAME

# oh-my-zshをユーザー用にもインストール
RUN sh -c "$(curl -fsSL https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh)" "" --unattended

# Claude Codeのインストール
RUN curl -fsSL https://claude.ai/install.sh | bash

# Node.js LTSとGemini CLIのインストール
USER root
RUN curl -fsSL https://deb.nodesource.com/setup_lts.x | bash - \
    && apt-get install -y nodejs \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && npm install -g @google/gemini-cli

# GitHub CLIのインストール（公式aptリポジトリ / amd64・arm64両対応）
RUN curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg \
        -o /usr/share/keyrings/githubcli-archive-keyring.gpg \
    && chmod go+r /usr/share/keyrings/githubcli-archive-keyring.gpg \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" \
        > /etc/apt/sources.list.d/github-cli.list \
    && apt-get update \
    && apt-get install -y gh \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# ghをgitのcredential helperに設定（HTTPSリモートへのpush/pull用）
# ~/.gitconfig はホストからread-onlyでマウントされるため、systemスコープ(/etc/gitconfig)に設定する
RUN git config --system credential."https://github.com".helper "!/usr/bin/gh auth git-credential" \
    && git config --system credential."https://gist.github.com".helper "!/usr/bin/gh auth git-credential"

USER $USERNAME

# ~/.config をdeveloper所有で作成しておく
# （先に作らないと ~/.config/gh マウント時にDockerが親ディレクトリをroot所有で作ってしまう）
RUN mkdir -p /home/developer/.config

# 基本的な.zshrc設定
RUN echo 'export ZSH="$HOME/.oh-my-zsh"' >> ~/.zshrc \
    && echo 'ZSH_THEME="robbyrussell"' >> ~/.zshrc \
    && echo 'plugins=(git)' >> ~/.zshrc \
    && echo 'source $ZSH/oh-my-zsh.sh' >> ~/.zshrc \
    && echo 'source /usr/share/zsh-autosuggestions/zsh-autosuggestions.zsh' >> ~/.zshrc \
    && echo 'source /usr/share/zsh-syntax-highlighting/zsh-syntax-highlighting.zsh' >> ~/.zshrc

# 作業ディレクトリ設定
WORKDIR /workspaces

# デフォルトシェルをzshに設定
ENV SHELL=/bin/zsh