# app/services/dictionary_service.py
import os
import json
import pickle
import csv
import random
from typing import Optional, Dict, List, Tuple
from app.config.settings import settings
from app.schemas.word import WordCreate
from app.database.connection import get_db_connection
from app.services.translation_service import TranslationService

class GermanDictionaryService:
    """Main workflow orchestrator with integrated dictionary processing"""
    
    def __init__(self):
        self.morph_dict = {}       # word -> [analyses] (for article processor)
        self.noun_dict = {}        # word -> {gender: [plurals]} (for plural processor)
        self.cache_loaded = False
        self.ai_service = None
        
    def set_ai_service(self, ai_service):
        """Inject AI service dependency"""
        self.ai_service = ai_service
        
    async def initialize(self):
        """Load all dictionary data"""
        print("🔄 Loading German dictionaries...")
        
        success_morph = await self._build_morph_dict_cache()
        success_noun = await self._build_noun_dict_cache()
        
        if success_morph and success_noun:
            self.cache_loaded = True
            print("✅ All dictionaries loaded successfully")
            return True
        else:
            print("❌ Dictionary loading failed")
            return False
    
    async def process_word_complete(self, word_id: int, word_data: WordCreate, request_id: str) -> Dict:
        """Main workflow entry point - follows workflow.txt exactly"""
        
        if not self.cache_loaded:
            raise Exception("Dictionary service not initialized")
        if not self.ai_service:
            raise Exception("AI service not injected")
        
        word = word_data.word.strip()
        context = word_data.context_sentence
        review_flags = []
        
        print(f"🚀 WORKFLOW START: '{word}' (Request: {request_id})")
        if context:
            print(f"   📝 Context: {context}")
        
        # STEP 1: Check if word has article
        has_article, article, clean_word = self._check_has_article(word)
        
        if has_article:
            print(f"   ✅ Has article: {article} {clean_word} → Go to plural processing")
            return await self._step4_plural_processing(clean_word, article, context, review_flags, word_id, word_data, request_id)
        
        # STEP 2: Check if word is noun
        print(f"   🔍 No article → Checking word type...")
        word_analysis = self.process_word(word)
        
        if word_analysis['type'] != 'noun':
            print(f"   ✅ Not a noun ({word_analysis['type']}) → Generate sentence")
            return await self._step5_generate_sentence(word, word_analysis['type'], context, review_flags, word_id, word_data, request_id)
        
        print(f"   ✅ Is a noun → Get article")
        
        # STEP 3: Get article process
        article = await self._step3_get_article(word, word_analysis, context, review_flags)
        
        # STEP 4: Plural processing
        return await self._step4_plural_processing(word, article, context, review_flags, word_id, word_data, request_id)
    
    def _check_has_article(self, word: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """Check if word already has an article"""
        parts = word.strip().split()
        if len(parts) == 2 and parts[0].lower() in ['der', 'die', 'das']:
            return True, parts[0], parts[1]
        return False, None, word
    
    async def _step3_get_article(self, word: str, word_analysis: dict, context: Optional[str], review_flags: list) -> str:
        """STEP 3: Get article process"""
        
        articles = word_analysis['articles']
        print(f"   🔍 Found {len(articles)} articles: {articles}")
        
        if not articles:
            print(f"   🤖 No article found → AI generation + REVIEW FLAG")
            article = await self.ai_service.generate_article(word, context)
            review_flags.append("generated_article")
            print(f"   ✅ AI generated: '{article}'")
            return article
            
        elif len(articles) == 1:
            article = articles[0]
            print(f"   ✅ Single match: '{article}'")
            return article
            
        else:
            print(f"   ⚠️  Multiple articles: {articles}")
            
            if context:
                print(f"   🤖 Using AI with context + REVIEW FLAG")
                article = await self.ai_service.generate_article(word, context)
                review_flags.append("context_article_selection")
                print(f"   ✅ AI selected: '{article}'")
                return article
            else:
                article = random.choice(articles)
                review_flags.append("random_article_selection")
                print(f"   🎲 Random selection: '{article}' + REVIEW FLAG")
                return article
    
    async def _step4_plural_processing(self, word: str, article: str, context: Optional[str], review_flags: list, word_id: int, word_data: WordCreate, request_id: str) -> Dict:
        """STEP 4: Plural processing"""
        
        combined_word = f"{article} {word}"
        print(f"   🔍 Plural lookup for: '{combined_word}'")
        
        plural_result = self.process_plural(combined_word)
        
        if plural_result['plurals']:
            plural = plural_result['plurals'][0]
            print(f"   ✅ Found plural: '{plural}'")
        else:
            print(f"   🤖 No plural found → AI generation + REVIEW FLAG")
            plural = await self.ai_service.generate_plural(combined_word, context)
            review_flags.append("generated_plural")
            print(f"   ✅ AI generated: '{plural}'")
        
        return await self._step5_generate_sentence(combined_word, 'noun', context, review_flags, word_id, word_data, request_id, plural)
    
    async def _step5_generate_sentence(self, word: str, word_type: str, context: Optional[str], review_flags: list, word_id: int, word_data: WordCreate, request_id: str, plural: Optional[str] = None) -> Dict:
        """STEP 5: Generate sentence (main exit point)"""
        
        print(f"   🤖 Generating sentence for: '{word}' ({word_type})")
        
        sentence = await self.ai_service.generate_sentence(word, word_type, context)
        print(f"   ✅ Generated sentence: '{sentence}'")
        
        print(f"   🌐 Translating...")
        translation = await TranslationService.translate_text(sentence)
        word_translation = await TranslationService.translate_text(word)
        print(f"   ✅ Translations complete")
        
        result = {
            'tl_word': word,
            'tl_sentence': sentence,
            'nl_word': word_translation,
            'nl_sentence': translation,
            'tl_plural': plural,
            'word_type': word_type,
            'processing_path': 'workflow_v2',
            'review_flags': review_flags
        }
        
        await self._save_processed_word(word_id, word_data, result, request_id)
        
        print(f"✅ COMPLETED: '{word}' → '{word_translation}' (sentence: '{sentence}' → '{translation}')")
        if plural:
            print(f"   📌 Plural: {plural}")
        if review_flags:
            print(f"   ⚠️  Review flags: {review_flags}")
        print("-" * 60)
        
        return result
    
    async def _save_processed_word(self, word_id: int, word_data: WordCreate, result: Dict, request_id: str):
        """Save processed word to database"""
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                review_flags_json = json.dumps(result['review_flags']) if result['review_flags'] else None
                
                cursor.execute("""
                    INSERT INTO processed_words 
                    (original_word, date, tl_word, nl_word, tl_sentence, nl_sentence, tl_plural, review_flags)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    word_data.word, 
                    word_data.date, 
                    result['tl_word'], 
                    result['nl_word'], 
                    result['tl_sentence'], 
                    result['nl_sentence'], 
                    result['tl_plural'],
                    review_flags_json
                ))
                
                cursor.execute("DELETE FROM pending_words WHERE id = ?", (word_id,))
                conn.commit()
            
            print(f"   💾 Saved to database")
            
        except Exception as e:
            print(f"   ❌ Database save failed: {str(e)}")
            raise e
    
    def process_word(self, word: str) -> dict:
        """Process a word and return analysis results"""
        
        analyses = self.morph_dict.get(word) or self.morph_dict.get(word.lower())
        
        if not analyses:
            return {'word': word, 'type': None, 'articles': []}
        
        word_type = None
        articles = set()
        
        for analysis in analyses:
            parts = analysis.split(' ', 1)
            if len(parts) != 2:
                continue
                
            category_and_attrs = parts[1]
            
            if ',' in category_and_attrs:
                category_parts = category_and_attrs.split(',')
                category = category_parts[0]
                attributes = category_parts[1:]
            else:
                category = category_and_attrs
                attributes = []
            
            if category in ['NN', 'NNP']:
                word_type = 'noun'
                for attr in attributes:
                    attr = attr.strip()
                    if attr == 'masc':
                        articles.add('der')
                    elif attr == 'fem':
                        articles.add('die')
                    elif attr == 'neut':
                        articles.add('das')
            elif category == 'V':
                word_type = 'verb'
            elif category == 'ADJ':
                word_type = 'adjective'
            elif category == 'ADV':
                word_type = 'adverb'
            elif category == 'ART':
                word_type = 'article'
            elif category == 'PREP':
                word_type = 'preposition'
            elif category == 'CONJ':
                word_type = 'conjunction'
        
        return {
            'word': word,
            'type': word_type,
            'articles': sorted(list(articles))
        }
    
    def process_plural(self, combined_word: str) -> dict:
        """Process a combined word and return analysis results"""
        
        parts = combined_word.strip().split()
        if len(parts) != 2:
            return {'word': combined_word, 'plurals': []}
        
        article, word = parts
        word_lower = word.lower()
        
        gender_map = {'der': 'm', 'die': 'f', 'das': 'n'}
        expected_gender = gender_map.get(article.lower())
        
        if not expected_gender or word_lower not in self.noun_dict:
            return {'word': word, 'plurals': []}
        
        word_genders = self.noun_dict[word_lower]
        
        if expected_gender not in word_genders:
            return {'word': word, 'plurals': []}
        
        plurals = word_genders[expected_gender]
        return {'word': word, 'plurals': plurals}
    
    async def _build_morph_dict_cache(self) -> bool:
        """Build morph_dict for process_word function"""
        morphology_file = settings.MORPHOLOGY_DICT_PATH
        cache_path = os.path.join(settings.DICT_CACHE_DIR, "morph_dict.pkl")
        
        if not os.path.exists(morphology_file):
            print(f"❌ Missing morphology file: {morphology_file}")
            return False
        
        if os.path.exists(cache_path):
            print("📖 Loading morph_dict from cache...")
            try:
                with open(cache_path, 'rb') as f:
                    self.morph_dict = pickle.load(f)
                print(f"✅ Morph dict loaded from cache: {len(self.morph_dict):,} word forms")
                return True
            except Exception as e:
                print(f"⚠️  Cache corrupted, rebuilding: {e}")
        
        print(f"📖 Building morph_dict from {morphology_file}...")
        
        try:
            with open(morphology_file, 'r', encoding='utf-8', errors='ignore') as f:
                lines = [line.strip() for line in f.readlines()]
            
            print(f"   📊 Read {len(lines):,} lines")
            
            i = 0
            processed_words = 0
            while i < len(lines):
                line = lines[i]
                
                if not line or line.startswith('#'):
                    i += 1
                    continue
                
                if ' ' not in line:
                    word_form = line
                    
                    j = i + 1
                    analyses = []
                    while j < len(lines):
                        next_line = lines[j]
                        if not next_line or next_line.startswith('#'):
                            j += 1
                            continue
                        if ' ' not in next_line:
                            break
                        analyses.append(next_line)
                        j += 1
                    
                    if word_form not in self.morph_dict:
                        self.morph_dict[word_form] = []
                    self.morph_dict[word_form].extend(analyses)
                    processed_words += 1
                    
                    if processed_words % 50000 == 0:
                        print(f"   🔄 Processed {processed_words:,} words...")
                    
                    i = j
                else:
                    i += 1
            
            print(f"   💾 Caching to {cache_path}...")
            with open(cache_path, 'wb') as f:
                pickle.dump(self.morph_dict, f)
            
            print(f"✅ Morph dict built: {len(self.morph_dict):,} word forms")
            return True
            
        except Exception as e:
            print(f"❌ Morph dict building error: {e}")
            return False
    
    async def _build_noun_dict_cache(self) -> bool:
        """Build noun_dict for process_plural function"""
        csv_file = settings.NOUNS_CSV_PATH
        cache_path = os.path.join(settings.DICT_CACHE_DIR, "noun_dict.pkl")
        
        if not os.path.exists(csv_file):
            print(f"❌ Missing nouns CSV file: {csv_file}")
            return False
        
        if os.path.exists(cache_path):
            print("📖 Loading noun_dict from cache...")
            try:
                with open(cache_path, 'rb') as f:
                    self.noun_dict = pickle.load(f)
                print(f"✅ Noun dict loaded from cache: {len(self.noun_dict):,} nouns")
                return True
            except Exception as e:
                print(f"⚠️  Cache corrupted, rebuilding: {e}")
        
        print(f"📖 Building noun_dict from {csv_file}...")
        
        try:
            processed_rows = 0
            valid_nouns = 0
            
            with open(csv_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                
                for row in reader:
                    processed_rows += 1
                    
                    lemma = row.get('lemma', '').strip()
                    pos = row.get('pos', '').strip()
                    
                    if processed_rows % 5000 == 0:
                        print(f"   🔄 Processed {processed_rows:,} rows, found {valid_nouns:,} valid nouns...")
                    
                    if not lemma or 'Substantiv' not in pos or lemma.startswith('-') or lemma.endswith('-'):
                        continue
                    
                    lemma_lower = lemma.lower()
                    if lemma_lower not in self.noun_dict:
                        self.noun_dict[lemma_lower] = {}
                    
                    pairs = []
                    
                    main_genus = row.get('genus', '').strip()
                    if main_genus in ['m', 'f', 'n']:
                        for col in ['nominativ plural', 'nominativ plural*', 'nominativ plural 1', 'nominativ plural 2']:
                            plural = row.get(col, '').strip()
                            if plural:
                                pairs.append((main_genus, plural))
                    
                    for i in range(1, 5):
                        genus = row.get(f'genus {i}', '').strip()
                        if genus in ['m', 'f', 'n']:
                            for col in ['nominativ plural', f'nominativ plural {i}']:
                                plural = row.get(col, '').strip()
                                if plural:
                                    pairs.append((genus, plural))
                    
                    if pairs:
                        valid_nouns += 1
                        for gender, plural in pairs:
                            if gender not in self.noun_dict[lemma_lower]:
                                self.noun_dict[lemma_lower][gender] = []
                            if plural not in self.noun_dict[lemma_lower][gender]:
                                self.noun_dict[lemma_lower][gender].append(plural)
            
            print(f"   💾 Caching to {cache_path}...")
            with open(cache_path, 'wb') as f:
                pickle.dump(self.noun_dict, f)
            
            print(f"✅ Noun dict built:")
            print(f"   📊 Processed {processed_rows:,} total rows")
            print(f"   📊 Found {valid_nouns:,} valid nouns")
            print(f"   📊 Final size: {len(self.noun_dict):,} entries")
            return True
            
        except Exception as e:
            print(f"❌ Noun dict building error: {e}")
            return False