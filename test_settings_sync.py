#!/usr/bin/env python3
"""
Settings Sync テスト用ファイル
VS Codeでこのファイルを開いて、拡張機能の動作を確認
"""

def test_extensions():
    """拡張機能の動作テスト"""
    print("🔍 VS Code拡張機能テスト")
    
    # Python拡張機能のテスト
    data = [1, 2, 3, 4, 5]
    result = sum(data)
    print(f"Python拡張機能: {result}")
    
    # Black Formatterテスト (保存時に自動フォーマットされるか)
    poorly_formatted_code={
        "test":"value",
        "another":  "value"
    }
    
    # Flake8テスト (警告が表示されるか)
    unused_variable = "これは使われていない変数"
    
    # GitLensテスト (Git履歴が表示されるか)
    return "拡張機能テスト完了"

if __name__ == "__main__":
    test_extensions() 