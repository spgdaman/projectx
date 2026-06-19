import { useState } from 'react';
import { View, Text, TouchableOpacity, Modal, FlatList, StyleSheet } from 'react-native';
import { colors } from '../theme';

export const COUNTRY_CODES = [
  { code: '+254', flag: '🇰🇪', name: 'Kenya' },
  { code: '+256', flag: '🇺🇬', name: 'Uganda' },
  { code: '+255', flag: '🇹🇿', name: 'Tanzania' },
  { code: '+250', flag: '🇷🇼', name: 'Rwanda' },
  { code: '+251', flag: '🇪🇹', name: 'Ethiopia' },
  { code: '+234', flag: '🇳🇬', name: 'Nigeria' },
  { code: '+233', flag: '🇬🇭', name: 'Ghana' },
  { code: '+27', flag: '🇿🇦', name: 'South Africa' },
  { code: '+260', flag: '🇿🇲', name: 'Zambia' },
  { code: '+263', flag: '🇿🇼', name: 'Zimbabwe' },
  { code: '+267', flag: '🇧🇼', name: 'Botswana' },
  { code: '+1', flag: '🇺🇸', name: 'USA / Canada' },
  { code: '+44', flag: '🇬🇧', name: 'United Kingdom' },
  { code: '+91', flag: '🇮🇳', name: 'India' },
  { code: '+971', flag: '🇦🇪', name: 'UAE' },
];

export function buildFullPhone(countryCode: string, localNumber: string): string {
  const local = localNumber.trim();
  return countryCode + (local.startsWith('0') ? local.slice(1) : local);
}

interface Props {
  value: string;
  onChange: (code: string) => void;
}

export function CountryCodePicker({ value, onChange }: Props) {
  const [open, setOpen] = useState(false);
  const selected = COUNTRY_CODES.find((c) => c.code === value) ?? COUNTRY_CODES[0];

  return (
    <>
      <TouchableOpacity style={s.trigger} onPress={() => setOpen(true)} activeOpacity={0.7}>
        <Text style={s.triggerText}>{selected.flag} {selected.code}</Text>
        <Text style={s.caret}>▾</Text>
      </TouchableOpacity>

      <Modal visible={open} animationType="slide" transparent>
        <View style={s.overlay}>
          <View style={s.sheet}>
            <View style={s.sheetHeader}>
              <Text style={s.sheetTitle}>Select Country</Text>
              <TouchableOpacity onPress={() => setOpen(false)} hitSlop={{ top: 8, bottom: 8, left: 8, right: 8 }}>
                <Text style={s.closeBtn}>✕</Text>
              </TouchableOpacity>
            </View>
            <FlatList
              data={COUNTRY_CODES}
              keyExtractor={(item) => item.code}
              renderItem={({ item }) => (
                <TouchableOpacity
                  style={[s.option, item.code === value && s.optionSelected]}
                  onPress={() => { onChange(item.code); setOpen(false); }}
                  activeOpacity={0.7}
                >
                  <Text style={s.optionFlag}>{item.flag}</Text>
                  <Text style={s.optionName}>{item.name}</Text>
                  <Text style={s.optionCode}>{item.code}</Text>
                </TouchableOpacity>
              )}
            />
          </View>
        </View>
      </Modal>
    </>
  );
}

const s = StyleSheet.create({
  trigger: {
    flexDirection: 'row', alignItems: 'center', gap: 4,
    backgroundColor: '#f9fafb', borderWidth: 1, borderColor: colors.border,
    borderTopLeftRadius: 12, borderBottomLeftRadius: 12,
    paddingHorizontal: 12, paddingVertical: 13,
  },
  triggerText: { fontSize: 15, color: colors.textPrimary },
  caret: { fontSize: 10, color: colors.textMuted, marginLeft: 2 },
  overlay: { flex: 1, backgroundColor: 'rgba(0,0,0,0.45)', justifyContent: 'flex-end' },
  sheet: { backgroundColor: colors.surface, borderTopLeftRadius: 20, borderTopRightRadius: 20, maxHeight: '70%' },
  sheetHeader: {
    flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center',
    padding: 20, borderBottomWidth: 1, borderColor: colors.border,
  },
  sheetTitle: { fontSize: 17, fontWeight: '700', color: colors.textPrimary },
  closeBtn: { fontSize: 18, color: colors.textMuted },
  option: {
    flexDirection: 'row', alignItems: 'center', gap: 12,
    paddingHorizontal: 20, paddingVertical: 14,
    borderBottomWidth: 1, borderColor: '#f3f4f6',
  },
  optionSelected: { backgroundColor: colors.primaryLight },
  optionFlag: { fontSize: 22 },
  optionName: { flex: 1, fontSize: 15, color: colors.textPrimary },
  optionCode: { fontSize: 14, color: colors.textSecondary, fontWeight: '600' },
});
