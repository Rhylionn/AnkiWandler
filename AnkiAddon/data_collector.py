# data_collector.py - Flexible Data Collection System
from typing import Dict, Any
from abc import ABC, abstractmethod

class BaseDataCollector(ABC):
    """Base class for data collectors"""
    
    @abstractmethod
    def collect(self) -> Dict[str, Any]:
        """Collect data and return as dictionary"""
        pass
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Return collector name"""
        pass

class CardDataCollector(BaseDataCollector):
    """Collector for card data"""
    
    def __init__(self, card_processor):
        self.card_processor = card_processor
        self.deck_name = None
    
    @property
    def name(self) -> str:
        return "cards"
    
    def collect(self) -> Dict[str, Any]:
        """Collect current card data from deck"""
        if not self.deck_name:
            return {"cards": []}
        
        try:
            cards = self.card_processor.extract_cards_from_deck(self.deck_name)
            return {
                "cards": cards,
                "count": len(cards),
                "deck_name": self.deck_name
            }
        except Exception as e:
            print(f"Error collecting cards: {e}")
            return {"cards": [], "error": str(e)}
    
    def set_deck_name(self, deck_name: str):
        """Set the deck to collect cards from"""
        self.deck_name = deck_name

# Future collectors - ready for implementation

class ReviewDataCollector(BaseDataCollector):
    """Collector for review statistics (future implementation)"""
    
    @property
    def name(self) -> str:
        return "reviews"
    
    def collect(self) -> Dict[str, Any]:
        """Collect review statistics"""
        # TODO: Implement review data collection
        # This would collect:
        # - Recent review sessions
        # - Success rates
        # - Time spent studying
        # - Card difficulty ratings
        return {
            "reviews": [],
            "stats": {},
            "note": "Review collection not yet implemented"
        }

class DeckDataCollector(BaseDataCollector):
    """Collector for deck metadata (future implementation)"""
    
    @property
    def name(self) -> str:
        return "decks"
    
    def collect(self) -> Dict[str, Any]:
        """Collect deck metadata"""
        # TODO: Implement deck data collection
        # This would collect:
        # - Deck names and IDs
        # - Card counts per deck
        # - Deck creation dates
        # - Deck configurations
        return {
            "decks": [],
            "note": "Deck collection not yet implemented"
        }

class StudyPatternCollector(BaseDataCollector):
    """Collector for study patterns (future implementation)"""
    
    @property
    def name(self) -> str:
        return "patterns"
    
    def collect(self) -> Dict[str, Any]:
        """Collect study patterns"""
        # TODO: Implement study pattern collection
        # This would collect:
        # - Study time patterns
        # - Frequency of study sessions
        # - Performance trends
        # - Learning velocity
        return {
            "patterns": {},
            "note": "Pattern collection not yet implemented"
        }

class DataCollector:
    """Flexible data collection manager"""
    
    def __init__(self):
        self.collectors = {}
    
    def register_collector(self, collector: BaseDataCollector) -> None:
        """Register a data collector"""
        self.collectors[collector.name] = collector
        print(f"Registered data collector: {collector.name}")
    
    def unregister_collector(self, name: str) -> None:
        """Remove a data collector"""
        if name in self.collectors:
            del self.collectors[name]
            print(f"Unregistered data collector: {name}")
    
    def get_collector(self, name: str) -> BaseDataCollector:
        """Get a specific collector"""
        return self.collectors.get(name)
    
    def list_collectors(self) -> list:
        """List all registered collectors"""
        return list(self.collectors.keys())
    
    def collect_enabled_data(self, config_manager) -> Dict[str, Any]:
        """Collect data from all enabled collectors"""
        enabled_collectors = config_manager.get_enabled_collectors()
        collected_data = {}
        
        for collector_name in enabled_collectors:
            if collector_name in self.collectors:
                try:
                    collector = self.collectors[collector_name]
                    data = collector.collect()
                    collected_data[collector_name] = data
                    print(f"Collected data from {collector_name}")
                except Exception as e:
                    print(f"Failed to collect data from {collector_name}: {e}")
                    collected_data[collector_name] = {"error": str(e)}
        
        return collected_data
    
    def collect_all_data(self) -> Dict[str, Any]:
        """Collect data from all collectors (regardless of config)"""
        collected_data = {}
        
        for name, collector in self.collectors.items():
            try:
                data = collector.collect()
                collected_data[name] = data
            except Exception as e:
                print(f"Failed to collect data from {name}: {e}")
                collected_data[name] = {"error": str(e)}
        
        return collected_data