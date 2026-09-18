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

# ---- OpenMontage 動画制作ツールチェーン ----

# FFmpeg と日本語フォント
# FFmpeg は約15ツール（合成・結合・字幕焼き込み・音声ミックス）が依存する必須コンポーネント。
# fonts-noto-cjk は字幕/キャプションに日本語を焼き込む際の豆腐化を防ぐ。
RUN apt-get update && apt-get install -y \
    ffmpeg \
    fontconfig \
    fonts-noto-cjk \
    fonts-dejavu-core \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Python ツールチェーン（OpenMontage は Python 3.10+ が必須）
# ubuntu:22.04 の python3 は 3.10 だが pip / venv / ensurepip が同梱されないため
# 明示的に導入する（これが無いと `make setup` の venv 作成が失敗する）。
# python-is-python3 は AGENT_GUIDE.md の手順が `python -c ...` を前提にしているため。
RUN apt-get update && apt-get install -y \
    python3-pip \
    python3-venv \
    python3-dev \
    python-is-python3 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Chromium ヘッドレス実行用の共有ライブラリ
# Remotion / HyperFrames は Chrome Headless Shell でフレームを描画する。
# シェル本体は初回レンダリング時に自動ダウンロードされるが、これらの .so が無いと
# "libnspr4.so: cannot open shared object file" で起動に失敗する。
RUN apt-get update && apt-get install -y \
    libnspr4 \
    libnss3 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libatspi2.0-0 \
    libcups2 \
    libdrm2 \
    libgbm1 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libasound2 \
    libpango-1.0-0 \
    libcairo2 \
    libxshmfence1 \
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

# HyperFrames / Remotion 用の Chromium（Playwright ビルドを流用）
# HyperFrames は Linux ARM64 向けの Chrome Headless Shell を配布していないため
# （`npx hyperframes browser ensure` が「手動で用意せよ」と言って失敗する）、
# Playwright の正規 Chromium ビルドを固定パスへ入れて参照させる。
# Ubuntu 22.04 の chromium-browser は snap 移行用スタブ(v85)でコンテナでは動かないので使わない。
# アーキテクチャ差を吸収するためバイナリは glob で探して symlink する。
ENV PLAYWRIGHT_BROWSERS_PATH=/opt/playwright
RUN mkdir -p /opt/playwright \
    && npx -y playwright@latest install chromium \
    && CHROME_BIN="$(find /opt/playwright -maxdepth 3 -type f -name chrome | head -n 1)" \
    && HEADLESS_BIN="$(find /opt/playwright -maxdepth 3 -type f -name chrome-headless-shell | head -n 1)" \
    && ln -sf "$CHROME_BIN" /usr/local/bin/chromium \
    && ln -sf "$HEADLESS_BIN" /usr/local/bin/chrome-headless-shell \
    && /usr/local/bin/chromium --version \
    && npm cache clean --force

# HyperFrames にこの Chromium を使わせる
ENV HYPERFRAMES_BROWSER_PATH=/usr/local/bin/chrome-headless-shell

# Remotion にも同じ Chromium を使わせる。
# Remotion は自前の Chrome Headless Shell を初回レンダリング時に
# ダウンロードするが、この環境ではそれが zygote の起動に失敗し
# "Timed out after 25000 ms while trying to connect to the browser" で
# レンダリングが止まる。上で入れた Playwright ビルドは正常に動くため
# そちらを使わせる。video_compose は Remotion を内部で呼ぶので
# CLI フラグ(--browser-executable)ではなく環境変数で効かせる必要がある。
ENV REMOTION_BROWSER_EXECUTABLE=/usr/local/bin/chrome-headless-shell

# VOICEVOX ENGINE（無料・オフラインの日本語TTS）
# piper には日本語音声が存在しないため、APIキー無しで日本語ナレーションを作る
# 唯一の手段がこれ。HTTPサーバ(127.0.0.1:50021)として動作し、
# tools/audio/voicevox_tts.py が初回利用時に自動起動する。
#
# 注意: 展開後 約2.1GB あり、イメージサイズがその分増える。
# 不要なら --build-arg INSTALL_VOICEVOX=false でスキップできる。
#
# ライセンス: 商用・非商用問わず無料。ただし「VOICEVOX:<キャラクター名>」等の
# クレジット表記が必須で、キャラクターごとに個別規約がある。
# https://voicevox.hiroshiba.jp/term/
ARG INSTALL_VOICEVOX=true
ARG VOICEVOX_VERSION=0.25.2
RUN if [ "$INSTALL_VOICEVOX" = "true" ]; then \
        set -eux; \
        apt-get update && apt-get install -y --no-install-recommends p7zip-full; \
        case "$(dpkg --print-architecture)" in \
            arm64) VV_ARCH=linux-cpu-arm64 ;; \
            amd64) VV_ARCH=linux-cpu-x64 ;; \
            *) echo "unsupported arch for VOICEVOX" && exit 1 ;; \
        esac; \
        mkdir -p /tmp/vv /opt/voicevox; \
        curl -fsSL -o /tmp/vv/engine.7z.001 \
            "https://github.com/VOICEVOX/voicevox_engine/releases/download/${VOICEVOX_VERSION}/voicevox_engine-${VV_ARCH}-${VOICEVOX_VERSION}.7z.001"; \
        7z x -y -o/opt/voicevox /tmp/vv/engine.7z.001; \
        mv "/opt/voicevox/${VV_ARCH}" /opt/voicevox/engine; \
        rm -rf /tmp/vv; \
        chmod +x /opt/voicevox/engine/run; \
        apt-get clean; \
        rm -rf /var/lib/apt/lists/*; \
    fi

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
    && echo 'source /usr/share/zsh-syntax-highlighting/zsh-syntax-highlighting.zsh' >> ~/.zshrc \
    && echo '' >> ~/.zshrc \
    && echo '# OpenMontage: プロジェクトの venv があれば自動で有効化する' >> ~/.zshrc \
    && echo '# （piper_tts など PATH 上のバイナリを見るツールが shutil.which で検出できるようにするため）' >> ~/.zshrc \
    && echo '[ -f /workspaces/OpenMontage/.venv/bin/activate ] && source /workspaces/OpenMontage/.venv/bin/activate' >> ~/.zshrc

# 作業ディレクトリ設定
WORKDIR /workspaces

# デフォルトシェルをzshに設定
ENV SHELL=/bin/zsh