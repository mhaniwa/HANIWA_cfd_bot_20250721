#!/usr/bin/env python3
"""
Notion Integration Test Script
"""

import requests
import json
from datetime import datetime

def test_notion_integration():
    """Notion Integration テスト"""
    print("🚀 HANIWA CFD BOT - Notion Integration テスト")
    print("=" * 50)
    
    # トークンの入力
    print("💡 Notion Integration Token を入力してください:")
    print("   https://www.notion.so/my-integrations から取得")
    token = input("Token: ").strip()
    
    if not token:
        print("❌ トークンが入力されていません。")
        return False
    
    # API設定
    headers = {
        "Authorization": f"Bearer {token}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json"
    }
    
    # 基本接続テスト
    print("\n🔄 API接続テスト...")
    try:
        response = requests.get("https://api.notion.com/v1/users/me", headers=headers)
        
        if response.status_code == 200:
            user_data = response.json()
            print("✅ API接続成功！")
            print(f"   ユーザー名: {user_data.get('name', 'N/A')}")
            print(f"   ユーザーID: {user_data.get('id', 'N/A')}")
            
            # ページ検索テスト
            print("\n🔍 ページ検索テスト...")
            search_response = requests.post(
                "https://api.notion.com/v1/search",
                headers=headers,
                json={"filter": {"property": "object", "value": "page"}}
            )
            
            if search_response.status_code == 200:
                pages = search_response.json().get('results', [])
                print(f"✅ ページ検索成功！")
                print(f"   見つかったページ数: {len(pages)}")
                
                if pages:
                    for page in pages[:3]:
                        title = page.get('properties', {}).get('title', {}).get('title', [])
                        page_name = title[0].get('plain_text', 'Untitled') if title else 'Untitled'
                        print(f"   - {page_name}")
                
                print("\n🎉 テスト完了！")
                print("💡 Notion Integrationは正常に動作しています。")
                return True
            else:
                print(f"❌ ページ検索失敗: {search_response.status_code}")
                print(f"   エラー: {search_response.text}")
                return False
                
        else:
            print(f"❌ API接続失敗: {response.status_code}")
            print(f"   エラー: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ エラーが発生しました: {str(e)}")
        return False

if __name__ == "__main__":
    success = test_notion_integration()
    print("\n" + "=" * 50)
    if success:
        print("✅ テスト成功！")
    else:
        print("❌ テスト失敗！")
        print("💡 以下を確認してください:")
        print("   - Notion Integration Token が正しいか")
        print("   - ワークスペースでIntegrationを共有しているか")
        print("   - インターネット接続が正常か") 