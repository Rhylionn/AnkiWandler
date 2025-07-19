# app/services/dictionary_service.py
import os
import json
import pickle
import re
from typing import Optional, Dict, List, Tuple, Set
from collections import defaultdict, Counter
from app.config.settings import settings

class GermanDictionaryService:
    """German dictionary service using advanced logic from plural.py and test.py"""
    
    def __init__(self):
        self.morphology_data = {}  # word -> [(type, gender, lemma, article), ...]
        self.kaikki_data = {}      # word -> [{'gender': str, 'plural': str, 'article': str}, ...]
        self.singular_to_plural = {}  # Advanced plural mappings from plural.py logic
        self.word_forms = {}       # word -> (gender, case, number) for plural extraction
        self.stem_groups = defaultdict(list)  # stem -> [(word, gender, case, number)]
        self.cache_loaded = False
        
        # German morphological knowledge from plural.py
        self.umlaut_pairs = [('a', 'ä'), ('o', 'ö'), ('u', 'ü'), ('A', 'Ä'), ('O', 'Ö'), ('U', 'Ü')]
        
    async def initialize(self):
        """Load dictionary data (rebuild cache every restart)"""
        print("🔄 Loading German dictionaries...")
        
        success_morphology = await self._build_morphology_cache()
        success_kaikki = await self._build_kaikki_cache()
        success_plurals = await self._build_advanced_plural_cache()
        
        if success_morphology and success_kaikki and success_plurals:
            self.cache_loaded = True
            print("✅ All dictionaries loaded successfully")
        else:
            print("❌ Some dictionary loading failed")
            
        return self.cache_loaded
    
    async def _build_morphology_cache(self) -> bool:
        """Build morphology cache using test.py logic with proper case handling"""
        morphology_file = settings.MORPHOLOGY_DICT_PATH
        
        if not os.path.exists(morphology_file):
            print(f"❌ Missing morphology file: {morphology_file}")
            return False
        
        print(f"📖 Processing morphology dictionary...")
        
        # Use separate storage for case-sensitive and case-insensitive data
        temp_data = defaultdict(lambda: defaultdict(list))
        total_lines = 0
        
        try:
            with open(morphology_file, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    total_lines += 1
                    
                    if total_lines % 1000000 == 0:
                        print(f"   📊 Processed {total_lines//1000000}M morphology lines...")
                    
                    line = line.strip()
                    if not line:
                        continue
                    
                    # Parse: word_form + space + morphology (same as test.py)
                    parts = line.split(' ', 1)
                    if len(parts) != 2:
                        continue
                    
                    word_form_original = parts[0].strip()  # Keep original case
                    morphology = parts[1].strip()
                    
                    # Parse morphology
                    morph_parts = morphology.split(',')
                    if not morph_parts:
                        continue
                    
                    word_type = morph_parts[0].strip()
                    
                    # Store noun entries 
                    if word_type == 'NN':  # Noun
                        gender = self._extract_gender(morph_parts)
                        if gender:
                            article = self._get_article(gender)
                            entry = ('noun', gender, word_form_original, article)
                            
                            # Store with EXACT original case first
                            temp_data[word_form_original]['noun'].append(entry)
                            
                            # Store for plural extraction (plural.py logic)
                            case, number = self._extract_case_number(morph_parts)
                            if case and number:
                                self.word_forms[word_form_original] = (gender, case, number)
                    
                    elif word_type in ['V', 'ADJ', 'ADV', 'ART', 'PREP', 'CONJ', 'PRON', 'NUM', 'PART']:
                        simplified_type = self._simplify_word_type(word_type)
                        entry = (simplified_type, None, word_form_original, None)
                        
                        # Store with EXACT original case first
                        temp_data[word_form_original][simplified_type].append(entry)
        
        except Exception as e:
            print(f"❌ Morphology processing error: {e}")
            return False
        
        # Process collected data with proper case handling
        self.morphology_data = {}
        multiple_genders = 0
        
        for word_form, word_types in temp_data.items():
            if 'noun' in word_types and len(word_types['noun']) > 1:
                multiple_genders += 1
                self.morphology_data[word_form] = word_types['noun']
            elif 'noun' in word_types:
                self.morphology_data[word_form] = word_types['noun']
            else:
                # Non-noun - take first entry for each type
                all_entries = []
                for word_type, entries in word_types.items():
                    if entries:
                        all_entries.append(entries[0])
                
                if all_entries:
                    self.morphology_data[word_form] = all_entries
        
        print(f"✅ Morphology processed: {len(self.morphology_data):,} words, {multiple_genders:,} with multiple genders")
        
        # Debug: Check specific words
        self._debug_word_lookup("gehen")
        self._debug_word_lookup("Gehen")
        self._debug_word_lookup("Hund")
        self._debug_word_lookup("hund")
        
        return True
    
    def _extract_case_number(self, morph_parts) -> Tuple[Optional[str], Optional[str]]:
        """Extract case and number from morphology parts (plural.py logic)"""
        case = number = None
        
        for part in morph_parts[1:]:
            part = part.strip().lower()
            if part in ['nom', 'acc', 'dat', 'gen']:
                case = part
            elif part in ['sing', 'plu']:
                number = part
        
        return case, number
    
    async def _build_kaikki_cache(self) -> bool:
        """Build Kaikki cache using enhanced kaikki.py logic"""
        kaikki_file = settings.KAIKKI_DICT_PATH
        
        if not os.path.exists(kaikki_file):
            print(f"❌ Missing Kaikki file: {kaikki_file}")
            return False
        
        print(f"📖 Processing Kaikki dictionary...")
        
        total_lines = 0
        entries_with_plurals = 0
        
        try:
            with open(kaikki_file, 'r', encoding='utf-8') as f:
                for line in f:
                    total_lines += 1
                    
                    if total_lines % 100000 == 0:
                        print(f"   📊 Processed {total_lines//100000}00k Kaikki lines...")
                    
                    if not line.strip():
                        continue
                    
                    try:
                        entry = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    
                    # Only process German nouns (same as kaikki.py)
                    if (entry.get('lang') != 'German' or 
                        entry.get('pos') not in ['noun', 'Noun']):
                        continue
                    
                    word = entry.get('word', '').strip().lower()
                    if not word:
                        continue
                    
                    # Extract gender and plural (enhanced kaikki.py logic)
                    gender_info = self._extract_gender_and_plural_enhanced(entry)
                    if gender_info:
                        if word not in self.kaikki_data:
                            self.kaikki_data[word] = []
                        
                        self.kaikki_data[word].append({
                            'gender': gender_info['gender'],
                            'plural': gender_info['plural'],
                            'article': self._gender_to_article(gender_info['gender']),
                        })
                        
                        if gender_info['plural']:
                            entries_with_plurals += 1
            
            print(f"✅ Kaikki processed: {len(self.kaikki_data):,} words, {entries_with_plurals:,} with plurals")
            return True
            
        except Exception as e:
            print(f"❌ Kaikki processing error: {e}")
            return False
    
    def _extract_gender_and_plural_enhanced(self, entry: dict) -> Optional[Dict]:
        """Enhanced gender and plural extraction from Kaikki (better than kaikki.py)"""
        gender = self._extract_gender_from_kaikki_enhanced(entry)
        if not gender:
            return None
        
        plural = self._extract_plural_from_kaikki_enhanced(entry)
        
        return {
            'gender': gender,
            'plural': plural
        }
    
    def _extract_gender_from_kaikki_enhanced(self, entry: dict) -> Optional[str]:
        """Enhanced gender extraction from Kaikki (more thorough than kaikki.py)"""
        
        # Method 1: Head templates (same as kaikki.py)
        head_templates = entry.get('head_templates', [])
        for template in head_templates:
            if isinstance(template, dict):
                expansion = template.get('expansion', '')
                
                # Look for gender markers in expansion
                if ' m ' in expansion or expansion.endswith(' m') or 'masculine' in expansion:
                    return 'masculine'
                elif ' f ' in expansion or expansion.endswith(' f') or 'feminine' in expansion:
                    return 'feminine'
                elif ' n ' in expansion or expansion.endswith(' n') or 'neuter' in expansion:
                    return 'neuter'
                
                # Check args
                args = template.get('args', {})
                for key in ['1', 'g', 'gender']:
                    if key in args:
                        gender_val = args[key].strip().lower()
                        if gender_val in ['m', 'masc', 'masculine']:
                            return 'masculine'
                        elif gender_val in ['f', 'fem', 'feminine']:
                            return 'feminine'
                        elif gender_val in ['n', 'neut', 'neuter']:
                            return 'neuter'
        
        # Method 2: Check inflection templates
        inflection_templates = entry.get('inflection_templates', [])
        for template in inflection_templates:
            if isinstance(template, dict):
                args = template.get('args', {})
                for key, value in args.items():
                    if 'gender' in key.lower() or key in ['g', '1']:
                        gender_val = value.strip().lower()
                        if gender_val in ['m', 'masc', 'masculine']:
                            return 'masculine'
                        elif gender_val in ['f', 'fem', 'feminine']:
                            return 'feminine'
                        elif gender_val in ['n', 'neut', 'neuter']:
                            return 'neuter'
        
        # Method 3: Check forms for gender indicators
        forms = entry.get('forms', [])
        for form_info in forms:
            if isinstance(form_info, dict):
                tags = form_info.get('tags', [])
                for tag in tags:
                    if tag in ['masculine', 'feminine', 'neuter']:
                        return tag
        
        return None
    
    def _extract_plural_from_kaikki_enhanced(self, entry: dict) -> Optional[str]:
        """Enhanced plural extraction from Kaikki (more thorough than kaikki.py)"""
        
        forms = entry.get('forms', [])
        
        # Priority 1: Nominative plural
        for form_info in forms:
            if isinstance(form_info, dict):
                tags = form_info.get('tags', [])
                form = form_info.get('form', '').strip()
                
                if form and 'plural' in tags and 'nominative' in tags:
                    return form
        
        # Priority 2: Any plural with case info
        for form_info in forms:
            if isinstance(form_info, dict):
                tags = form_info.get('tags', [])
                form = form_info.get('form', '').strip()
                
                if form and 'plural' in tags and any(case in tags for case in ['nominative', 'accusative', 'dative', 'genitive']):
                    return form
        
        # Priority 3: Any plural form
        for form_info in forms:
            if isinstance(form_info, dict):
                tags = form_info.get('tags', [])
                form = form_info.get('form', '').strip()
                
                if form and 'plural' in tags:
                    return form
        
        # Priority 4: Check inflection templates for plural
        inflection_templates = entry.get('inflection_templates', [])
        for template in inflection_templates:
            if isinstance(template, dict):
                args = template.get('args', {})
                for key, value in args.items():
                    if 'plural' in key.lower() or key in ['2', 'pl']:
                        plural_val = value.strip()
                        if plural_val and plural_val != '-':
                            return plural_val
        
        return None
    
    async def _build_advanced_plural_cache(self) -> bool:
        """Build advanced plural cache using plural.py logic"""
        print(f"📖 Building advanced plural mappings...")
        
        # Step 1: Group words by stems (plural.py logic)
        self._group_by_stems_advanced()
        
        # Step 2: Find singular-plural pairs within stem groups
        pairs_found = self._find_pairs_in_groups_advanced()
        
        print(f"✅ Advanced plurals: {pairs_found:,} mappings created")
        return True
    
    def _group_by_stems_advanced(self):
        """Group words by stems using plural.py logic"""
        for word, (gender, case, number) in self.word_forms.items():
            stems = self._generate_possible_stems(word, case, number)
            
            # Add to all possible stem groups
            for stem in stems:
                self.stem_groups[stem].append((word, gender, case, number))
    
    def _generate_possible_stems(self, word: str, case: str, number: str) -> Set[str]:
        """Generate possible stems using plural.py logic"""
        stems = set()
        word_lower = word.lower()
        
        # Base stem
        stems.add(word_lower)
        
        # Remove common case/number endings
        if number == 'sing':
            # Singular endings to remove
            if case == 'gen' and word_lower.endswith('es'):
                stems.add(word_lower[:-2])
            elif case == 'gen' and word_lower.endswith('s'):
                stems.add(word_lower[:-1])
            elif case == 'dat' and word_lower.endswith('e'):
                stems.add(word_lower[:-1])
        
        elif number == 'plu':
            # Plural endings to remove
            endings_to_try = ['e', 'en', 'er', 's', 'nen']
            for ending in endings_to_try:
                if word_lower.endswith(ending):
                    stem = word_lower[:-len(ending)]
                    if len(stem) >= 2:  # Minimum stem length
                        stems.add(stem)
                        
                        # Also try with umlaut reversions
                        for umlaut, normal in self.umlaut_pairs:
                            if umlaut.lower() in stem:
                                stem_no_umlaut = stem.replace(umlaut.lower(), normal.lower())
                                stems.add(stem_no_umlaut)
        
        # Try umlaut variations for any stem
        for stem in list(stems):
            for umlaut, normal in self.umlaut_pairs:
                if umlaut.lower() in stem:
                    stems.add(stem.replace(umlaut.lower(), normal.lower()))
                if normal.lower() in stem:
                    stems.add(stem.replace(normal.lower(), umlaut.lower()))
        
        return stems
    
    def _find_pairs_in_groups_advanced(self) -> int:
        """Find singular-plural pairs using plural.py logic"""
        pairs_found = 0
        
        for stem, word_entries in self.stem_groups.items():
            if len(word_entries) < 2:
                continue
            
            # Separate by number
            singulars = [(w, g, c) for w, g, c, n in word_entries if n == 'sing']
            plurals = [(w, g, c) for w, g, c, n in word_entries if n == 'plu']
            
            if not singulars or not plurals:
                continue
            
            # Find best pairs (same gender, nominative case preferred)
            best_singular = self._find_best_form(singulars, 'nom')
            best_plural = self._find_best_form(plurals, 'nom')
            
            if best_singular and best_plural:
                # Ensure same gender
                sing_gender = next((g for w, g, c in singulars if w == best_singular), None)
                plur_gender = next((g for w, g, c in plurals if w == best_plural), None)
                
                if sing_gender == plur_gender:
                    # Map all singular forms to the best plural
                    for word, gender, case in singulars:
                        if gender == sing_gender:
                            self.singular_to_plural[word] = best_plural
                            # Also map capitalized version
                            self.singular_to_plural[word.capitalize()] = best_plural.capitalize()
                    
                    pairs_found += 1
        
        return pairs_found
    
    def _find_best_form(self, forms: List[Tuple[str, str, str]], preferred_case: str = 'nom') -> Optional[str]:
        """Find the best form from a list (word, gender, case)"""
        if not forms:
            return None
        
        # Try to find preferred case
        for word, gender, case in forms:
            if case == preferred_case:
                return word
        
        # Fallback to any form, prefer shortest
        return min(forms, key=lambda x: len(x[0]))[0]
    
    def _extract_gender(self, morph_parts):
        """Extract gender from morphology parts (test.py logic)"""
        for part in morph_parts[1:]:
            part = part.strip()
            if part in ['masc', 'fem', 'neut']:
                return part
        return None
    
    def _get_article(self, gender: str) -> str:
        """Get article from gender (test.py logic)"""
        return {'masc': 'der', 'fem': 'die', 'neut': 'das'}.get(gender, 'der')
    
    def _gender_to_article(self, gender: str) -> str:
        """Convert gender to article (kaikki.py logic)"""
        gender_map = {
            'masculine': 'der',
            'feminine': 'die',
            'neuter': 'das',
            'masc': 'der',
            'fem': 'die', 
            'neut': 'das'
        }
        return gender_map.get(gender, 'der')
    
    def _simplify_word_type(self, word_type: str) -> str:
        """Simplify word type (test.py logic)"""
        type_map = {
            'V': 'verb',
            'ADJ': 'adjective', 
            'ADV': 'adverb',
            'ART': 'article',
            'PREP': 'preposition',
            'CONJ': 'conjunction',
            'PRON': 'pronoun',
            'NUM': 'number',
            'PART': 'particle'
        }
        return type_map.get(word_type, word_type.lower())
    
    def _debug_word_lookup(self, word: str):
        """Debug method to check word lookup"""
        if word in self.morphology_data:
            entries = self.morphology_data[word]
            types = [entry[0] for entry in entries]
            print(f"   🔍 DEBUG: '{word}' → {types}")
    
    async def determine_word_type(self, word: str) -> Optional[str]:
        """Determine word type using enhanced case-sensitive logic"""
        if not self.cache_loaded:
            return None
        
        # Strategy 1: EXACT case-sensitive lookup first
        if word in self.morphology_data:
            entries = self.morphology_data[word]
            types = [entry[0] for entry in entries]
            result = Counter(types).most_common(1)[0][0] if types else None
            print(f"   🔍 Case-sensitive lookup: '{word}' → {result}")
            return result
        
        # Strategy 2: Case-insensitive fallback
        if word.lower() in self.morphology_data:
            entries = self.morphology_data[word.lower()]
            types = [entry[0] for entry in entries]
            result = Counter(types).most_common(1)[0][0] if types else None
            print(f"   🔍 Case-insensitive lookup: '{word}' → {result}")
            return result
        
        # Strategy 3: Try capitalized version if original was lowercase
        if word[0].islower() and word.capitalize() in self.morphology_data:
            entries = self.morphology_data[word.capitalize()]
            types = [entry[0] for entry in entries]
            result = Counter(types).most_common(1)[0][0] if types else None
            print(f"   🔍 Capitalized lookup: '{word}' → {result}")
            return result
            
        print(f"   🔍 Not found: '{word}'")
        return None
    
    async def is_word_plural(self, word: str) -> bool:
        """Check if word is already plural according to morphology"""
        if not self.cache_loaded:
            return False
        
        # Strategy 1: EXACT case-sensitive check first
        if word in self.word_forms:
            gender, case, number = self.word_forms[word]
            result = number == 'plu'
            print(f"   🔍 Plural check case-sensitive: '{word}' → {result}")
            return result
        
        # Strategy 2: Case-insensitive check
        if word.lower() in self.word_forms:
            gender, case, number = self.word_forms[word.lower()]
            result = number == 'plu'
            print(f"   🔍 Plural check case-insensitive: '{word}' → {result}")
            return result
        
        print(f"   🔍 Plural check not found: '{word}'")
        return False
    
    async def get_article_for_noun(self, word: str) -> Optional[str]:
        """Get article using enhanced case-sensitive logic with multiple strategies"""
        if not self.cache_loaded:
            return None
        
        # Strategy 1: EXACT case-sensitive lookup first
        if word in self.morphology_data:
            entries = self.morphology_data[word]
            nouns = [e for e in entries if e[0] == 'noun']
            
            if len(nouns) == 1:
                result = nouns[0][3]  # article
                print(f"   🔍 Article case-sensitive: '{word}' → {result}")
                return result
            elif len(nouns) > 1:
                # Multiple genders - return most common
                articles = [entry[3] for entry in nouns]
                result = Counter(articles).most_common(1)[0][0]
                print(f"   🔍 Article case-sensitive (multi): '{word}' → {result}")
                return result
        
        # Strategy 2: Case-insensitive fallback
        if word.lower() in self.morphology_data:
            entries = self.morphology_data[word.lower()]
            nouns = [e for e in entries if e[0] == 'noun']
            
            if len(nouns) == 1:
                result = nouns[0][3]  # article
                print(f"   🔍 Article case-insensitive: '{word}' → {result}")
                return result
            elif len(nouns) > 1:
                # Multiple genders - return most common
                articles = [entry[3] for entry in nouns]
                result = Counter(articles).most_common(1)[0][0]
                print(f"   🔍 Article case-insensitive (multi): '{word}' → {result}")
                return result
        
        # Strategy 3: Try capitalized variant if original was lowercase
        if word[0].islower() and word.capitalize() in self.morphology_data:
            capitalized_entries = self.morphology_data[word.capitalize()]
            capitalized_nouns = [e for e in capitalized_entries if e[0] == 'noun']
            
            if len(capitalized_nouns) == 1:
                result = capitalized_nouns[0][3]
                print(f"   🔍 Article capitalized: '{word}' → {result}")
                return result
            elif len(capitalized_nouns) > 1:
                articles = [entry[3] for entry in capitalized_nouns]
                result = Counter(articles).most_common(1)[0][0]
                print(f"   🔍 Article capitalized (multi): '{word}' → {result}")
                return result
        
        print(f"   🔍 Article not found: '{word}'")
        return None
    
    async def get_plural_advanced(self, word_with_article: str) -> Optional[str]:
        """Get plural using multiple strategies (enhanced from plural.py)"""
        if not self.cache_loaded:
            return None
            
        parts = word_with_article.strip().split()
        if len(parts) != 2:
            return None
            
        article, word = parts
        
        # Strategy 1: Kaikki lookup (enhanced)
        kaikki_result = await self.get_plural_from_kaikki(word_with_article)
        if kaikki_result:
            return kaikki_result
        
        # Strategy 2: Advanced morphology patterns (plural.py logic)
        morphology_result = self._get_plural_from_morphology(word)
        if morphology_result:
            return morphology_result
        
        return None
    
    async def get_plural_from_kaikki(self, word_with_article: str) -> Optional[str]:
        """Get plural using enhanced kaikki.py logic"""
        if not self.cache_loaded:
            return None
            
        parts = word_with_article.strip().split()
        if len(parts) != 2:
            return None
            
        article, word = parts
        entries = self.kaikki_data.get(word.lower(), [])
        
        # Find matching gender (kaikki.py logic)
        for entry in entries:
            if entry['article'].lower() == article.lower():
                return entry['plural']
        return None
    
    def _get_plural_from_morphology(self, word: str) -> Optional[str]:
        """Get plural using advanced morphology patterns (plural.py logic)"""
        
        # Strategy 1: Direct lookup from advanced mappings
        if word in self.singular_to_plural:
            return self.singular_to_plural[word]
        
        # Strategy 2: Try capitalized/lowercase variants
        variants = [word.lower(), word.capitalize(), word.upper()]
        for variant in variants:
            if variant in self.singular_to_plural:
                # Preserve original capitalization pattern
                result = self.singular_to_plural[variant]
                if word[0].isupper():
                    return result.capitalize()
                return result.lower()
        
        return None