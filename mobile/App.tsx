import { StatusBar } from 'expo-status-bar';
import * as ImagePicker from 'expo-image-picker';
import * as SecureStore from 'expo-secure-store';
import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  ActivityIndicator,
  Alert,
  FlatList,
  Image,
  KeyboardAvoidingView,
  Modal,
  Platform,
  Pressable,
  RefreshControl,
  SafeAreaView,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native';
import {
  api,
  DEMO_FEED,
  DEMO_USER,
  mediaUrl,
  type FeedItem,
  type OpenItem,
} from './src/api';

type Tab = 'home' | 'explore' | 'opens' | 'profile';

const colors = {
  canvas: '#0B0D13',
  surface: '#141722',
  elevated: '#1B1F2C',
  border: '#2A3040',
  text: '#F8FAFC',
  muted: '#9AA4B5',
  violet: '#7C3AED',
  violetLight: '#A78BFA',
  gold: '#F4D38A',
  green: '#34D399',
  red: '#FB7185',
};

class RuntimeErrorBoundary extends React.Component<React.PropsWithChildren, { error: string | null }> {
  state: { error: string | null } = { error: null };

  static getDerivedStateFromError(error: unknown) {
    return { error: error instanceof Error ? error.message : String(error) };
  }

  render() {
    if (this.state.error) {
      return (
        <SafeAreaView style={styles.safeArea}>
          <StatusBar style="light" />
          <View style={styles.errorContainer}>
            <Text style={styles.errorEmoji}>!</Text>
            <Text style={styles.errorTitle}>SPREEGO could not load</Text>
            <Text style={styles.errorMessage}>{this.state.error}</Text>
            <Text style={styles.errorHint}>Restart Expo with: npx expo start --lan --clear</Text>
          </View>
        </SafeAreaView>
      );
    }
    return this.props.children;
  }
}

function SpreegoApp() {
  const [activeTab, setActiveTab] = useState<Tab>('home');
  const [feed, setFeed] = useState<FeedItem[]>(DEMO_FEED);
  const [opens, setOpens] = useState<OpenItem[]>([]);
  const [token, setToken] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [authVisible, setAuthVisible] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [identifier, setIdentifier] = useState('');
  const [password, setPassword] = useState('');

  const loadContent = useCallback(async (refresh = false) => {
    if (refresh) setRefreshing(true);
    else setLoading(false);
    try {
      const [feedResult, opensResult] = await Promise.all([api.getFeed(), api.getOpens()]);
      setFeed(feedResult);
      setOpens(opensResult);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    SecureStore.getItemAsync('spreego_token').then(setToken).catch(() => undefined);
    loadContent();
  }, [loadContent]);

  const refreshControl = useMemo(
    () => <RefreshControl refreshing={refreshing} onRefresh={() => loadContent(true)} tintColor={colors.violetLight} />,
    [loadContent, refreshing],
  );

  const handleLogin = async () => {
    if (!identifier.trim() || !password) {
      Alert.alert('Login required', 'Enter your email/phone and password.');
      return;
    }
    try {
      const result = await api.login(identifier.trim(), password);
      await SecureStore.setItemAsync('spreego_token', result.access_token);
      setToken(result.access_token);
      setAuthVisible(false);
      setPassword('');
      Alert.alert('Welcome back', 'You are now signed in to SPREEGO.');
    } catch (error) {
      Alert.alert('Login failed', error instanceof Error ? error.message : 'Could not sign in.');
    }
  };

  const handleLogout = async () => {
    await SecureStore.deleteItemAsync('spreego_token');
    setToken(null);
  };

  const handleUpload = async (source: 'camera' | 'library') => {
    if (!token) {
      setAuthVisible(true);
      return;
    }
    try {
      const permission = source === 'camera'
        ? await ImagePicker.requestCameraPermissionsAsync()
        : await ImagePicker.requestMediaLibraryPermissionsAsync();
      if (!permission.granted) {
        Alert.alert('Permission required', 'Please allow camera or media access to upload a Spree.');
        return;
      }
      const result = source === 'camera'
        ? await ImagePicker.launchCameraAsync({ mediaTypes: ['images', 'videos'], quality: 0.85 })
        : await ImagePicker.launchImageLibraryAsync({ mediaTypes: ['images', 'videos'], quality: 0.85 });
      if (result.canceled || !result.assets?.[0]) return;

      setUploading(true);
      const asset = result.assets[0];
      await api.publishMedia(token, {
        uri: asset.uri,
        name: asset.fileName || `spree-${Date.now()}.${asset.type === 'video' ? 'mp4' : 'jpg'}`,
        type: asset.mimeType || (asset.type === 'video' ? 'video/mp4' : 'image/jpeg'),
      });
      Alert.alert('Spree published', 'Your new Spree is now live.');
      await loadContent(true);
      setActiveTab('home');
    } catch (error) {
      Alert.alert('Upload failed', error instanceof Error ? error.message : 'Could not publish this media.');
    } finally {
      setUploading(false);
    }
  };

  const clap = async (item: FeedItem) => {
    if (!token) {
      setAuthVisible(true);
      return;
    }
    try {
      const result = await api.clap(item.id, token);
      setFeed((current) => current.map((entry) => entry.id === item.id ? { ...entry, claps_count: result.newCount } : entry));
    } catch (error) {
      Alert.alert('Could not clap', error instanceof Error ? error.message : 'Please try again.');
    }
  };

  return (
    <SafeAreaView style={styles.safeArea}>
      <StatusBar style="light" />
      <View style={styles.app}>
        <Header activeTab={activeTab} onNotifications={() => Alert.alert('Notifications', 'Your latest activity will appear here.')} />
        {loading ? (
          <View style={styles.centered}><ActivityIndicator size="large" color={colors.violetLight} /><Text style={styles.mutedText}>Loading SPREEGO…</Text></View>
        ) : activeTab === 'opens' ? (
          <OpenList opens={opens} refreshControl={refreshControl} />
        ) : activeTab === 'profile' ? (
          <ProfileScreen
            token={token}
            uploading={uploading}
            onLogin={() => setAuthVisible(true)}
            onLogout={handleLogout}
            onUpload={handleUpload}
          />
        ) : (
          <FeedList
            items={feed}
            title={activeTab === 'explore' ? 'Explore' : 'For you'}
            refreshControl={refreshControl}
            onClap={clap}
          />
        )}
        <BottomNav activeTab={activeTab} onChange={setActiveTab} onCreate={() => handleUpload('camera')} />
      </View>
      <LoginModal
        visible={authVisible}
        identifier={identifier}
        password={password}
        onIdentifierChange={setIdentifier}
        onPasswordChange={setPassword}
        onClose={() => setAuthVisible(false)}
        onLogin={handleLogin}
      />
    </SafeAreaView>
  );
}

function Header({ activeTab, onNotifications }: { activeTab: Tab; onNotifications: () => void }) {
  return (
    <View style={styles.header}>
      <View>
        <Text style={styles.brand}>SPREEGO</Text>
        <Text style={styles.headerSubtitle}>{activeTab === 'opens' ? 'Community challenges' : 'Cinematic moments, made social'}</Text>
      </View>
      <Pressable style={styles.iconButton} onPress={onNotifications} accessibilityLabel="Notifications">
        <Text style={styles.iconText}>♢</Text>
      </Pressable>
    </View>
  );
}

function FeedList({ items, title, refreshControl, onClap }: { items: FeedItem[]; title: string; refreshControl: React.ReactElement; onClap: (item: FeedItem) => void }) {
  return (
    <FlatList
      data={items}
      keyExtractor={(item) => item.id}
      refreshControl={refreshControl}
      contentContainerStyle={styles.listContent}
      ListHeaderComponent={<View style={styles.sectionHeader}><Text style={styles.sectionTitle}>{title}</Text><Text style={styles.sectionMeta}>{items.length} stories</Text></View>}
      renderItem={({ item }) => <FeedCard item={item} onClap={() => onClap(item)} />}
      ListEmptyComponent={<EmptyState label="No Sprees yet" />}
      showsVerticalScrollIndicator={false}
    />
  );
}

function FeedCard({ item, onClap }: { item: FeedItem; onClap: () => void }) {
  return (
    <View style={styles.card}>
      <View style={styles.creatorRow}>
        <Image source={{ uri: mediaUrl(item.creator.avatar_url) }} style={styles.avatar} />
        <View style={styles.creatorInfo}><Text style={styles.creatorName}>{item.creator.display_name}</Text><Text style={styles.handle}>{item.creator.handle || `@${item.creator.username}`}</Text></View>
        {item.sponsored ? <Text style={styles.sponsored}>SPONSORED</Text> : null}
      </View>
      <Image source={{ uri: mediaUrl(item.thumbnail_url || item.media_url) }} style={styles.heroImage} resizeMode="cover" />
      <View style={styles.cardBody}>
        <Text style={styles.cardTitle}>{item.title}</Text>
        {item.caption ? <Text style={styles.caption} numberOfLines={2}>{item.caption}</Text> : null}
        <View style={styles.actionRow}>
          <Pressable style={styles.actionButton} onPress={onClap}><Text style={styles.actionIcon}>👏</Text><Text style={styles.actionText}>{item.claps_count}</Text></Pressable>
          <Text style={styles.actionButton}><Text style={styles.actionIcon}>◌</Text><Text style={styles.actionText}>{item.comments_count}</Text></Text>
          <Text style={styles.actionButton}><Text style={styles.actionIcon}>↗</Text><Text style={styles.actionText}>{item.shares_count}</Text></Text>
          <Text style={styles.views}>{formatCount(item.views_count)} views</Text>
        </View>
      </View>
    </View>
  );
}

function OpenList({ opens, refreshControl }: { opens: OpenItem[]; refreshControl: React.ReactElement }) {
  return (
    <FlatList
      data={opens}
      keyExtractor={(item) => item.id}
      refreshControl={refreshControl}
      contentContainerStyle={styles.listContent}
      ListHeaderComponent={<View style={styles.sectionHeader}><Text style={styles.sectionTitle}>Opens</Text><Text style={styles.sectionMeta}>Join a challenge</Text></View>}
      renderItem={({ item }) => (
        <View style={styles.openCard}>
          {item.cover_image_url ? <Image source={{ uri: mediaUrl(item.cover_image_url) }} style={styles.openImage} /> : <View style={[styles.openImage, styles.openPlaceholder]}><Text style={styles.openEmoji}>✦</Text></View>}
          <View style={styles.openBody}><Text style={styles.openStatus}>{item.status}</Text><Text style={styles.openTitle}>{item.title}</Text><Text style={styles.caption} numberOfLines={2}>{item.description || 'Create something memorable and join the community.'}</Text><Text style={styles.openMeta}>{item.participants_count} participants · {item.submissions_count} submissions</Text></View>
        </View>
      )}
      ListEmptyComponent={<EmptyState label="No active Opens found" />}
      showsVerticalScrollIndicator={false}
    />
  );
}

function ProfileScreen({ token, uploading, onLogin, onLogout, onUpload }: { token: string | null; uploading: boolean; onLogin: () => void; onLogout: () => void; onUpload: (source: 'camera' | 'library') => void }) {
  return (
    <ScrollView contentContainerStyle={styles.profileContent} showsVerticalScrollIndicator={false}>
      <View style={styles.profileHero}><Image source={{ uri: DEMO_USER.avatar_url }} style={styles.profileAvatar} /><Text style={styles.profileName}>{DEMO_USER.display_name}</Text><Text style={styles.handle}>{token ? DEMO_USER.handle : 'Sign in to unlock your creator profile'}</Text><View style={styles.statsRow}><Stat label="Sprees" value={DEMO_USER.post_count} /><Stat label="Followers" value={DEMO_USER.follower_count} /><Stat label="Following" value={DEMO_USER.following_count} /></View></View>
      {token ? (
        <View style={styles.profilePanel}><Text style={styles.panelTitle}>Create something new</Text><Text style={styles.caption}>Capture a moment or pick media from your phone.</Text><View style={styles.twoButtons}><Button label={uploading ? 'Uploading…' : 'Open camera'} onPress={() => onUpload('camera')} disabled={uploading} /><Button label="Choose media" onPress={() => onUpload('library')} secondary disabled={uploading} /></View><Pressable onPress={onLogout} style={styles.logoutButton}><Text style={styles.logoutText}>Sign out</Text></Pressable></View>
      ) : (
        <View style={styles.profilePanel}><Text style={styles.panelTitle}>Welcome to SPREEGO</Text><Text style={styles.caption}>Sign in to clap, upload and join community Opens.</Text><Button label="Sign in" onPress={onLogin} /></View>
      )}
    </ScrollView>
  );
}

function Stat({ label, value }: { label: string; value: number }) { return <View style={styles.stat}><Text style={styles.statValue}>{formatCount(value)}</Text><Text style={styles.statLabel}>{label}</Text></View>; }

function Button({ label, onPress, secondary = false, disabled = false }: { label: string; onPress: () => void; secondary?: boolean; disabled?: boolean }) {
  return <Pressable disabled={disabled} onPress={onPress} style={[styles.button, secondary && styles.secondaryButton, disabled && styles.disabledButton]}><Text style={[styles.buttonText, secondary && styles.secondaryButtonText]}>{label}</Text></Pressable>;
}

function BottomNav({ activeTab, onChange, onCreate }: { activeTab: Tab; onChange: (tab: Tab) => void; onCreate: () => void }) {
  const items: Array<{ id: Tab; label: string; icon: string }> = [{ id: 'home', label: 'Home', icon: '⌂' }, { id: 'explore', label: 'Explore', icon: '⌕' }, { id: 'opens', label: 'Opens', icon: '✦' }, { id: 'profile', label: 'Profile', icon: '◉' }];
  return <View style={styles.bottomNav}>{items.slice(0, 2).map((item) => <NavItem key={item.id} item={item} activeTab={activeTab} onPress={() => onChange(item.id)} />)}<Pressable onPress={onCreate} style={styles.createButton}><Text style={styles.createIcon}>＋</Text></Pressable>{items.slice(2).map((item) => <NavItem key={item.id} item={item} activeTab={activeTab} onPress={() => onChange(item.id)} />)}</View>;
}

function NavItem({ item, activeTab, onPress }: { item: { id: Tab; label: string; icon: string }; activeTab: Tab; onPress: () => void }) { const active = item.id === activeTab; return <Pressable onPress={onPress} style={styles.navItem}><Text style={[styles.navIcon, active && styles.navActive]}>{item.icon}</Text><Text style={[styles.navLabel, active && styles.navActive]}>{item.label}</Text></Pressable>; }

function LoginModal({ visible, identifier, password, onIdentifierChange, onPasswordChange, onClose, onLogin }: { visible: boolean; identifier: string; password: string; onIdentifierChange: (value: string) => void; onPasswordChange: (value: string) => void; onClose: () => void; onLogin: () => void }) {
  return <Modal visible={visible} transparent animationType="slide" onRequestClose={onClose}><KeyboardAvoidingView style={styles.modalBackdrop} behavior={Platform.OS === 'ios' ? 'padding' : undefined}><View style={styles.modalCard}><View style={styles.modalHeader}><Text style={styles.panelTitle}>Sign in to SPREEGO</Text><Pressable onPress={onClose}><Text style={styles.closeText}>×</Text></Pressable></View><TextInput value={identifier} onChangeText={onIdentifierChange} placeholder="Email or phone" placeholderTextColor={colors.muted} autoCapitalize="none" style={styles.input} /><TextInput value={password} onChangeText={onPasswordChange} placeholder="Password" placeholderTextColor={colors.muted} secureTextEntry style={styles.input} /><Button label="Continue" onPress={onLogin} /></View></KeyboardAvoidingView></Modal>;
}

function EmptyState({ label }: { label: string }) { return <View style={styles.empty}><Text style={styles.emptyEmoji}>✦</Text><Text style={styles.emptyText}>{label}</Text></View>; }
function formatCount(value: number) { if (value >= 1000000) return `${(value / 1000000).toFixed(1)}M`; if (value >= 1000) return `${(value / 1000).toFixed(1)}K`; return String(value); }

const styles = StyleSheet.create({
  safeArea: { flex: 1, backgroundColor: colors.canvas },
  app: { flex: 1, backgroundColor: colors.canvas },
  header: { paddingHorizontal: 20, paddingVertical: 15, flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', borderBottomWidth: StyleSheet.hairlineWidth, borderBottomColor: colors.border },
  brand: { color: colors.text, fontSize: 21, fontWeight: '900', letterSpacing: 3 },
  headerSubtitle: { color: colors.muted, fontSize: 11, marginTop: 3 },
  iconButton: { width: 42, height: 42, borderRadius: 15, backgroundColor: colors.elevated, alignItems: 'center', justifyContent: 'center' },
  iconText: { color: colors.gold, fontSize: 23 },
  centered: { flex: 1, alignItems: 'center', justifyContent: 'center', gap: 12 },
  mutedText: { color: colors.muted, fontSize: 13 },
  listContent: { paddingHorizontal: 14, paddingBottom: 110, paddingTop: 15 },
  sectionHeader: { paddingHorizontal: 5, paddingBottom: 12, flexDirection: 'row', justifyContent: 'space-between', alignItems: 'baseline' },
  sectionTitle: { color: colors.text, fontSize: 24, fontWeight: '800' },
  sectionMeta: { color: colors.muted, fontSize: 12 },
  card: { backgroundColor: colors.surface, borderRadius: 24, marginBottom: 16, overflow: 'hidden', borderWidth: 1, borderColor: colors.border },
  creatorRow: { padding: 13, flexDirection: 'row', alignItems: 'center' },
  avatar: { width: 36, height: 36, borderRadius: 18, backgroundColor: colors.elevated },
  creatorInfo: { flex: 1, marginLeft: 10 },
  creatorName: { color: colors.text, fontSize: 13, fontWeight: '700' },
  handle: { color: colors.muted, fontSize: 11, marginTop: 2 },
  sponsored: { color: colors.gold, fontSize: 9, fontWeight: '800', letterSpacing: 1 },
  heroImage: { width: '100%', height: 310, backgroundColor: colors.elevated },
  cardBody: { padding: 14 },
  cardTitle: { color: colors.text, fontSize: 17, fontWeight: '800' },
  caption: { color: colors.muted, lineHeight: 19, fontSize: 12, marginTop: 5 },
  actionRow: { flexDirection: 'row', alignItems: 'center', marginTop: 14, gap: 14 },
  actionButton: { flexDirection: 'row', alignItems: 'center', gap: 5 },
  actionIcon: { color: colors.gold, fontSize: 16 },
  actionText: { color: colors.text, fontSize: 12, fontWeight: '600' },
  views: { color: colors.muted, fontSize: 11, marginLeft: 'auto' },
  openCard: { backgroundColor: colors.surface, borderRadius: 22, overflow: 'hidden', marginBottom: 14, borderWidth: 1, borderColor: colors.border },
  openImage: { width: '100%', height: 145, backgroundColor: colors.elevated },
  openPlaceholder: { alignItems: 'center', justifyContent: 'center' },
  openEmoji: { color: colors.gold, fontSize: 42 },
  openBody: { padding: 14 },
  openStatus: { color: colors.green, fontSize: 10, fontWeight: '800', letterSpacing: 1 },
  openTitle: { color: colors.text, fontSize: 18, fontWeight: '800', marginTop: 5 },
  openMeta: { color: colors.violetLight, fontSize: 11, marginTop: 12, fontWeight: '700' },
  profileContent: { padding: 16, paddingBottom: 120 },
  profileHero: { alignItems: 'center', paddingVertical: 20 },
  profileAvatar: { width: 92, height: 92, borderRadius: 46, borderWidth: 3, borderColor: colors.violetLight },
  profileName: { color: colors.text, fontSize: 23, fontWeight: '800', marginTop: 12 },
  statsRow: { flexDirection: 'row', gap: 30, marginTop: 24 },
  stat: { alignItems: 'center' },
  statValue: { color: colors.text, fontSize: 16, fontWeight: '800' },
  statLabel: { color: colors.muted, fontSize: 11, marginTop: 3 },
  profilePanel: { backgroundColor: colors.surface, borderRadius: 22, borderWidth: 1, borderColor: colors.border, padding: 18 },
  panelTitle: { color: colors.text, fontSize: 18, fontWeight: '800' },
  twoButtons: { flexDirection: 'row', gap: 10, marginTop: 18 },
  button: { flex: 1, backgroundColor: colors.violet, borderRadius: 13, minHeight: 46, alignItems: 'center', justifyContent: 'center', paddingHorizontal: 14 },
  buttonText: { color: '#fff', fontSize: 13, fontWeight: '800' },
  secondaryButton: { backgroundColor: colors.elevated, borderWidth: 1, borderColor: colors.border },
  secondaryButtonText: { color: colors.text },
  disabledButton: { opacity: 0.5 },
  logoutButton: { alignItems: 'center', marginTop: 18 },
  logoutText: { color: colors.red, fontSize: 12, fontWeight: '700' },
  bottomNav: { position: 'absolute', bottom: 10, left: 12, right: 12, height: 70, borderRadius: 23, backgroundColor: '#171A28F2', borderWidth: 1, borderColor: colors.border, flexDirection: 'row', alignItems: 'center', justifyContent: 'space-around', paddingHorizontal: 5 },
  navItem: { alignItems: 'center', justifyContent: 'center', width: 62, gap: 3 },
  navIcon: { color: colors.muted, fontSize: 22 },
  navLabel: { color: colors.muted, fontSize: 10, fontWeight: '600' },
  navActive: { color: colors.violetLight },
  createButton: { width: 52, height: 52, borderRadius: 18, backgroundColor: colors.violet, alignItems: 'center', justifyContent: 'center', marginTop: -22, borderWidth: 4, borderColor: colors.canvas },
  createIcon: { color: '#fff', fontSize: 32, lineHeight: 35, fontWeight: '300' },
  empty: { alignItems: 'center', paddingVertical: 80 },
  emptyEmoji: { color: colors.gold, fontSize: 35 },
  emptyText: { color: colors.muted, marginTop: 12 },
  errorContainer: { flex: 1, alignItems: 'center', justifyContent: 'center', padding: 28 },
  errorEmoji: { width: 46, height: 46, borderRadius: 23, backgroundColor: colors.red, color: '#fff', fontSize: 30, fontWeight: '900', textAlign: 'center', lineHeight: 46, marginBottom: 18 },
  errorTitle: { color: colors.text, fontSize: 22, fontWeight: '800', textAlign: 'center' },
  errorMessage: { color: colors.red, fontSize: 13, lineHeight: 20, textAlign: 'center', marginTop: 12 },
  errorHint: { color: colors.muted, fontSize: 12, lineHeight: 18, textAlign: 'center', marginTop: 18 },
  modalBackdrop: { flex: 1, backgroundColor: '#000000AA', justifyContent: 'flex-end' },
  modalCard: { backgroundColor: colors.surface, borderTopLeftRadius: 28, borderTopRightRadius: 28, padding: 22, paddingBottom: 34, borderWidth: 1, borderColor: colors.border, gap: 12 },
  modalHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 },
  closeText: { color: colors.muted, fontSize: 30, fontWeight: '300' },
  input: { backgroundColor: colors.elevated, borderWidth: 1, borderColor: colors.border, borderRadius: 13, height: 48, paddingHorizontal: 14, color: colors.text, fontSize: 14 },
});

export default function App() {
  return (
    <RuntimeErrorBoundary>
      <SpreegoApp />
    </RuntimeErrorBoundary>
  );
}
