# api_client.py - Server Communication
import json
import requests
from typing import List, Dict, Any, Optional, Tuple
from .utils import ensure_protocol

class APIClient:
    """Simple HTTP client for server communication"""
    
    def __init__(self, config_manager):
        self.config = config_manager
        self.timeout = 30
    
    def _get_headers(self) -> Dict[str, str]:
        """Get request headers with authentication"""
        return {
            "Authorization": f"Bearer {self.config.get('api_key')}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
    
    def _get_base_url(self) -> str:
        """Get base server URL"""
        url = self.config.get('server_url')
        return ensure_protocol(url, 'http')
    
    def _request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> Tuple[bool, Any]:
        """Make HTTP request to server"""
        try:
            url = f"{self._get_base_url()}{endpoint}"
            headers = self._get_headers()
            
            response = requests.request(
                method=method,
                url=url,
                headers=headers,
                json=data,
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                try:
                    return True, response.json()
                except json.JSONDecodeError:
                    return True, response.text
            else:
                error_msg = f"HTTP {response.status_code}"
                try:
                    error_data = response.json()
                    if 'detail' in error_data:
                        error_msg = error_data['detail']
                except:
                    error_msg = f"HTTP {response.status_code}: {response.text}"
                return False, error_msg
                
        except requests.exceptions.Timeout:
            return False, "Request timeout - server took too long to respond"
        except requests.exceptions.ConnectionError:
            return False, "Cannot connect to server - check URL and network"
        except Exception as e:
            return False, str(e)
    
    def test_connection(self) -> Tuple[bool, str]:
        """Test server connection"""
        success, result = self._request("GET", "/")
        if success:
            return True, "Connection successful"
        else:
            return False, f"Connection failed: {result}"
    
    def upload_cards(self, cards: List[Dict]) -> Tuple[bool, Any]:
        """Upload cards to server"""
        if not cards:
            return True, {"message": "No cards to upload", "cards_received": 0}
        
        success, result = self._request("POST", "/api/v1/anki/cards", {"cards": cards})
        return success, result
    
    def clear_cards(self) -> Tuple[bool, Any]:
        """Clear all cards from server"""
        success, result = self._request("DELETE", "/api/v1/anki/cards/clear_all")
        return success, result
    
    def get_words(self) -> Tuple[bool, List[Dict]]:
        """Get processed words from server"""
        success, result = self._request("GET", "/api/v1/words/processed?limit=100")
        if success:
            return True, result if isinstance(result, list) else []
        else:
            return False, []
    
    def clear_words(self) -> Tuple[bool, Any]:
        """Clear processed words from server"""
        success, result = self._request("DELETE", "/api/v1/words/processed/clear_all")
        return success, result
    
    def send_data(self, data_type: str, data: Dict) -> Tuple[bool, Any]:
        """Send specific data type to server (future extension point)"""
        endpoint = f"/api/v1/data/{data_type}"
        success, result = self._request("POST", endpoint, data)
        return success, result
    
    def send_bulk_data(self, all_data: Dict[str, Any]) -> Tuple[bool, Any]:
        """Send multiple data types in one request (future extension point)"""
        success, result = self._request("POST", "/api/v1/data/bulk", all_data)
        return success, result