from companion import backup, db


def test_backup_rotation(tmp_path):
    src = tmp_path / "c.db"
    c = db.connect(src)
    c.execute("INSERT INTO user_pref(key,value_json) VALUES ('x','1')"); c.commit()
    import time
    for _ in range(3):
        out = backup.backup(src, tmp_path / "bk", keep=2)
        time.sleep(1.05)
    files = sorted((tmp_path / "bk").glob("companion-*.db"))
    assert len(files) == 2
    r = db.connect(out).execute("SELECT value_json FROM user_pref WHERE key='x'").fetchone()
    assert r[0] == "1"
