cask "audaxdm" do
  version "1.6.1"

  arch arm: "arm64", intel: "x64"

  sha256 arm:   "57375ffb67801f0b1271a31cdb064e87a72b51f23294079725577854ba43a806",
         intel: "0798e6909851c62ea5297056730a237ced0c1795b75150ca538bc07360670dd4"

  url "https://github.com/commandprompt/audaxdm-tap/releases/download/test/audaxdm-#{version}_mac_#{arch}.dmg"
  name "Audax Data Manager"
  desc "Database management tool for PostgreSQL"
  homepage "https://github.com/commandprompt/audax-data-manager"

  livecheck do
    url :url
    regex(/^v?(\d+(?:\.\d+)+)(?:-release)?$/i)
    strategy :github_latest
  end

  depends_on macos: :ventura

  app "Audax Data Manager.app"

  zap trash: [
    "~/.pgmanage",
    "~/Library/Application Support/Audax Data Manager",
  ]

  caveats <<~EOS
    #{token} is not yet signed or notarized, so macOS blocks the first launch.
    Before opening the app, remove the quarantine flag:
      xattr -dr com.apple.quarantine "/Applications/Audax Data Manager.app"

    Alternatively, open the app once, then go to System Settings >
    Privacy & Security and click "Open Anyway".
  EOS
end
