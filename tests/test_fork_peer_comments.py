"""Fork only (FORK.md): comments inside a [Peer] block survive the panel's rewrites of the server config.

The amneziawg-installer (manage_amneziawg.sh) and the bots on top of it (awgram) know a client only by the
line `#_Name = <name>` right after its `[Peer]`. The panel used to drop every comment on its first write, and
the installer then lost all of its clients: `list` showed none, `remove` and the expiry cron failed."""
import os
import re
import sys
import tempfile
import unittest

os.environ.setdefault("DATA_DIR", tempfile.mkdtemp())
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app import awgserver  # noqa: E402

K1 = "HIgo9xNzJMWLKASShiTqIybxZ0U3wGLiUeJ1PKf8ykw="
K2 = "yAnz5TF+lXXJte14tji3zlMNq+hd2rYUIgJBgB3fBmk="
K3 = "Y+m1JcLUzvJW7JMvhLDEtF2X9r7wYADHHV355wLntQY="

# As the installer writes it (awg_common.sh, add peer)
INSTALLER_SERVER = f"""[Interface]
PrivateKey = {K2}
Address = 10.8.1.1/24
ListenPort = 443
Jc = 4
Jmin = 10
Jmax = 50
S1 = 12
S2 = 12
H1 = 1
H2 = 2
H3 = 3
H4 = 4

[Peer]
#_Name = alice
PublicKey = {K1}
PresharedKey = {K3}
AllowedIPs = 10.8.1.2/32

[Peer]
#_Name = bob-phone
PublicKey = {K3}
AllowedIPs = 10.8.1.3/32
"""


def names(text: str) -> list[str]:
    """What the installer sees: `grep '^#_Name = '`."""
    return re.findall(r"(?m)^#_Name = (.*)$", text)


class PeerCommentsTest(unittest.TestCase):
    def test_rewrite_keeps_installer_names(self):
        out = awgserver.parse(INSTALLER_SERVER).render()
        self.assertEqual(names(out), ["alice", "bob-phone"])
        # in the installer's own place: the line right after [Peer]
        self.assertIn(f"[Peer]\n#_Name = alice\nPublicKey = {K1}\n", out)
        self.assertIn(f"[Peer]\n#_Name = bob-phone\nPublicKey = {K3}\n", out)
        self.assertEqual(awgserver.parse(out).render(), out)

    def test_client_added_or_deleted_in_the_panel(self):
        sc = awgserver.parse(INSTALLER_SERVER)
        sc.peers.append(awgserver.Peer(K2, "", f"{sc.next_ip()}/32"))
        out = sc.render()
        self.assertEqual(names(out), ["alice", "bob-phone"])
        self.assertIn(f"[Peer]\nPublicKey = {K2}\nAllowedIPs = 10.8.1.4/32\n", out)
        sc = awgserver.parse(out)
        sc.peers = [p for p in sc.peers if p.public_key != K1]
        self.assertEqual(names(sc.render()), ["bob-phone"])

    def test_server_settings_saved(self):
        sc = awgserver.parse(INSTALLER_SERVER)
        sc.set("Jc", "5")
        sc.set("I1", "<r 2>")
        self.assertEqual(names(sc.render()), ["alice", "bob-phone"])

    def test_comments_never_reach_syncconf(self):
        st = awgserver.parse(INSTALLER_SERVER).stripped()
        self.assertNotIn("#", st)
        self.assertEqual(st.count("[Peer]"), 2)

    def test_disabled_client_is_hidden_from_the_installer(self):
        sc = awgserver.parse(INSTALLER_SERVER)
        sc.peer(K1).enabled = False
        out = sc.render()
        # The installer must not see a name in a disabled block: its `remove` drops the whole [Peer] block the
        # name is in, and for it a commented-out block is part of the [Peer] above, another client.
        self.assertEqual(names(out), ["bob-phone"])
        self.assertIn(f"{awgserver.DISABLED_MARK}\n# [Peer]\n# #_Name = alice\n# PublicKey = {K1}\n", out)
        again = awgserver.parse(out)
        self.assertEqual(again.render(), out)
        self.assertFalse(again.peer(K1).enabled)
        self.assertEqual([k for k, _ in again.peer(K1).extra], [])
        # turned on again: the name is back where the installer looks for it
        again.peer(K1).enabled = True
        self.assertIn(f"[Peer]\n#_Name = alice\nPublicKey = {K1}\n", again.render())

    def test_any_hash_comment_is_kept_as_is(self):
        text = INSTALLER_SERVER.replace("#_Name = bob-phone\n", "#_Name = bob-phone\n## note: 🙂 phone\n#\n")
        out = awgserver.parse(text).render()
        self.assertIn("#_Name = bob-phone\n## note: 🙂 phone\n#\nPublicKey", out)
        sc = awgserver.parse(out)
        sc.peer(K3).enabled = False
        again = awgserver.parse(sc.render())
        self.assertEqual(again.peer(K3).comments, ["#_Name = bob-phone", "## note: 🙂 phone", "#"])

    def test_semicolon_lines_are_still_dropped(self):
        # awg-quick doesn't take `;` for a comment: written back, such a line would reach the interface
        text = INSTALLER_SERVER.replace("#_Name = alice\n", "#_Name = alice\n; PostUp = touch /tmp/x\n")
        out = awgserver.parse(text).render()
        self.assertNotIn(";", out)
        self.assertEqual(names(out), ["alice", "bob-phone"])

    def test_backup_restore_keeps_names_without_control_characters(self):
        # foreign_ok checks the server config of a backup before it is restored
        text = INSTALLER_SERVER.replace("#_Name = alice\n", "#_Name = alice\n#x\x00y\n#\x1b[31mred\n#👨‍👩‍👧 family\n")
        sc = awgserver.parse(text)
        self.assertTrue(awgserver.foreign_ok(text, sc))
        self.assertEqual(sc.peer(K1).comments, ["#_Name = alice", "#👨‍👩‍👧 family"])   # ZWJ (Cf) stays
        self.assertNotIn("\x00", sc.render())

    def test_interface_comments_unchanged(self):
        # only [Peer] blocks keep comments; [Interface] keeps only its own `# I1..I5`, as before
        text = INSTALLER_SERVER.replace("ListenPort = 443\n", "ListenPort = 443\n# some note\n# I1 = <r 2>\n")
        out = awgserver.parse(text).render()
        self.assertNotIn("some note", out)
        self.assertIn("# I1 = <r 2>", out)


if __name__ == "__main__":
    unittest.main()
