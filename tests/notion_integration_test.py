#!/usr/bin/env python3
"""
Notion Integration Test Script
ステップ10で作成したNotion Integrationの動作テストを実行します。
"""

import os
import sys
import json
from datetime import datetime
import requests

# プロジェクトルートをパスに追加
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class NotionIntegrationTest:
    def __init__(self):
        self.base_url = "https://api.notion.com/v1"
        self.headers = {
            "Authorization": f"Bearer {self.get_notion_token()}",
            "Notion-Version": "2022-06-28",
            "Content-Type": "application/json"
        }
        
    def get_notion_token(self):
        """Notion APIトークンを取得（環境変数または入力）"""
        token = os.getenv('NOTION_TOKEN')
        if not token:
            print("⚠️  NOTION_TOKEN環境変数が設定されていません")
            print("💡 テスト用に一時的にトークンを入力してください：")
            print("   (本番環境では環境変数で設定してください)")
            token = input("Notion Integration Token: ").strip()
            if not token:
                raise ValueError("Notion APIトークンが必要です")
        return token
    
    def test_connection(self):
        """基本的な接続テスト"""
        print("🔄 Notion API接続テスト開始...")
        
        try:
            # ユーザー情報取得でAPIの基本動作確認
            response = requests.get(f"{self.base_url}/users/me", headers=self.headers)
            
            if response.status_code == 200:
                user_data = response.json()
                print("✅ API接続成功！")
                print(f"   ユーザー名: {user_data.get('name', 'N/A')}")
                print(f"   ユーザーID: {user_data.get('id', 'N/A')}")
                return True
            else:
                print(f"❌ API接続失敗: {response.status_code}")
                print(f"   エラー: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ 接続エラー: {str(e)}")
            return False
    
    def test_search_databases(self):
        """データベース検索テスト"""
        print("\n🔍 データベース検索テスト...")
        
        try:
            search_payload = {
                "filter": {
                    "property": "object",
                    "value": "database"
                }
            }
            
            response = requests.post(
                f"{self.base_url}/search", 
                headers=self.headers, 
                json=search_payload
            )
            
            if response.status_code == 200:
                search_data = response.json()
                databases = search_data.get('results', [])
                print(f"✅ データベース検索成功！")
                print(f"   見つかったデータベース数: {len(databases)}")
                
                for db in databases[:3]:  # 最初の3個を表示
                    title = db.get('title', [])
                    db_name = title[0].get('plain_text', 'Untitled') if title else 'Untitled'
                    print(f"   - {db_name} (ID: {db.get('id', 'N/A')})")
                
                return True
            else:
                print(f"❌ データベース検索失敗: {response.status_code}")
                print(f"   エラー: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ 検索エラー: {str(e)}")
            return False
    
    def test_create_page(self):
        """テストページ作成"""
        print("\n📝 テストページ作成...")
        
        try:
            # まず親ページを検索
            search_payload = {
                "filter": {
                    "property": "object",
                    "value": "page"
                }
            }
            
            response = requests.post(
                f"{self.base_url}/search", 
                headers=self.headers, 
                json=search_payload
            )
            
            if response.status_code != 200:
                print(f"❌ 親ページ検索失敗: {response.status_code}")
                return False
                
            pages = response.json().get('results', [])
            if not pages:
                print("⚠️  利用可能なページが見つかりません")
                print("💡 Notion Integration で該当のページを共有してください")
                return False
            
            # 最初のページを親として使用
            parent_page_id = pages[0]['id']
            parent_title = pages[0].get('properties', {}).get('title', {}).get('title', [])
            parent_name = parent_title[0].get('plain_text', 'Untitled') if parent_title else 'Untitled'
            
            print(f"   親ページ: {parent_name}")
            
            # テストページ作成
            page_payload = {
                "parent": {"page_id": parent_page_id},
                "properties": {
                    "title": {
                        "title": [
                            {
                                "text": {
                                    "content": f"HANIWA CFD BOT テスト - {datetime.now().strftime('%Y/%m/%d %H:%M')}"
                                }
                            }
                        ]
                    }
                },
                "children": [
                    {
                        "object": "block",
                        "type": "paragraph",
                        "paragraph": {
                            "rich_text": [
                                {
                                    "type": "text",
                                    "text": {
                                        "content": "✅ Notion Integration テスト成功！\n\nステップ10で作成したAPIインテグレーションが正常に動作しています。"
                                    }
                                }
                            ]
                        }
                    }
                ]
            }
            
            response = requests.post(
                f"{self.base_url}/pages", 
                headers=self.headers, 
                json=page_payload
            )
            
            if response.status_code == 200:
                page_data = response.json()
                print("✅ テストページ作成成功！")
                print(f"   ページID: {page_data.get('id', 'N/A')}")
                print(f"   URL: {page_data.get('url', 'N/A')}")
                return True
            else:
                print(f"❌ ページ作成失敗: {response.status_code}")
                print(f"   エラー: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ ページ作成エラー: {str(e)}")
            return False
    
    def run_all_tests(self):
        """すべてのテストを実行"""
        print("🚀 HANIWA CFD BOT - Notion Integration テスト")
        print("=" * 50)
        
        results = {
            "connection": self.test_connection(),
            "search": self.test_search_databases(),
            "create_page": self.test_create_page()
        }
        
        print("\n" + "=" * 50)
        print("📊 テスト結果サマリー")
        print("=" * 50)
        
        passed = sum(results.values())
        total = len(results)
        
        for test_name, result in results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"{test_name:15} : {status}")
        
        print(f"\n🎯 合計: {passed}/{total} テスト成功")
        
        if passed == total:
            print("🎉 すべてのテストが成功しました！")
            print("💡 Notion Integrationは正常に動作しています。")
        else:
            print("⚠️  一部のテストが失敗しました。")
            print("💡 Notion Integration の設定を確認してください。")
        
        return passed == total

if __name__ == "__main__":
    tester = NotionIntegrationTest()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1) 