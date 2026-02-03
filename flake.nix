{
  description = "axe-cli flake";
  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs?ref=nixpkgs-unstable";
    systems.url = "github:nix-systems/default";
    pyproject-nix = {
      url = "github:pyproject-nix/pyproject.nix";
      inputs.nixpkgs.follows = "nixpkgs";
    };
    uv2nix = {
      url = "github:pyproject-nix/uv2nix";
      inputs.pyproject-nix.follows = "pyproject-nix";
      inputs.nixpkgs.follows = "nixpkgs";
    };
    pyproject-build-systems = {
      url = "github:pyproject-nix/build-system-pkgs";
      inputs.pyproject-nix.follows = "pyproject-nix";
      inputs.uv2nix.follows = "uv2nix";
      inputs.nixpkgs.follows = "nixpkgs";
    };
  };
  outputs =
    {
      self,
      nixpkgs,
      systems,
      pyproject-nix,
      uv2nix,
      pyproject-build-systems,
    }:
    let
      allSystems = import systems;
      forAllSystems =
        f:
        nixpkgs.lib.genAttrs allSystems (
          system:
          let
            pkgs = import nixpkgs {
              inherit system;
              config.allowUnfree = true;
            };
          in
          f { inherit system pkgs; }
        );
    in
    {
      packages = forAllSystems (
        { pkgs, ... }:
        let
          axe-cli =
            let
              inherit (pkgs)
                lib
                callPackage
                python313
                runCommand
                ripgrep
                stdenvNoCC
                makeWrapper
                versionCheckHook
                ;
              python = python313;
              pyproject = lib.importTOML ./pyproject.toml;
              workspace = uv2nix.lib.workspace.loadWorkspace { workspaceRoot = ./.; };
              overlay = workspace.mkPyprojectOverlay {
                sourcePreference = "wheel";
              };
              extraBuildOverlay = final: prev: {
                # Add setuptools build dependency for ripgrepy
                ripgrepy = prev.ripgrepy.overrideAttrs (old: {
                  nativeBuildInputs = (old.nativeBuildInputs or [ ]) ++ [ final.setuptools ];
                });
                # Replace README symlink with real file for Nix builds.
                "axe-code" = prev."axe-code".overrideAttrs (old: {
                  postPatch = (old.postPatch or "") + ''
                    rm -f README.md
                    cp ${./README.md} README.md
                  '';
                });
              };
              pythonSet = (callPackage pyproject-nix.build.packages { inherit python; }).overrideScope (
                lib.composeManyExtensions [
                  pyproject-build-systems.overlays.wheel
                  overlay
                  extraBuildOverlay
                ]
              );
              axeCliPackage = pythonSet.mkVirtualEnv "axe-cli-virtual-env-${pyproject.project.version}" workspace.deps.default;
            in
            stdenvNoCC.mkDerivation ({
              pname = "axe-cli";
              version = pyproject.project.version;

              dontUnpack = true;

              nativeBuildInputs = [ makeWrapper ];
              buildInputs = [ ripgrep ];

              installPhase = ''
                runHook preInstall

                mkdir -p $out/bin
                makeWrapper ${axeCliPackage}/bin/axe $out/bin/axe \
                  --prefix PATH : ${lib.makeBinPath [ ripgrep ]} \
                  --set axe_CLI_NO_AUTO_UPDATE "1"

                runHook postInstall
              '';

              nativeInstallCheckInputs = [
                versionCheckHook
              ];
              versionCheckProgramArg = "--version";
              doInstallCheck = true;

              meta = {
                description = "axe Code CLI is a new CLI agent that can help you with your software development tasks and terminal operations";
                license = lib.licenses.asl20;
                sourceProvenance = with lib.sourceTypes; [ fromSource ];
                maintainers = with lib.maintainers; [
                  xiaoxiangmoe
                ];
                mainProgram = "axe";
              };
            });
        in
        {
          inherit axe-cli;
          default = axe-cli;
        }
      );
      formatter = forAllSystems ({ pkgs, ... }: pkgs.nixfmt-tree);
    };
}
