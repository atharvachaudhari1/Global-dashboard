import 'package:flutter/foundation.dart';
import 'package:google_sign_in/google_sign_in.dart';

class AuthProvider extends ChangeNotifier {
  final GoogleSignIn _googleSignIn = GoogleSignIn(
    scopes: <String>['email', 'profile'],
  );

  GoogleSignInAccount? _user;
  bool _isLoading = false;
  String? _error;

  GoogleSignInAccount? get user => _user;
  bool get isLoading => _isLoading;
  String? get error => _error;
  bool get isAuthenticated => _user != null;

  Future<void> tryRestoreSession() async {
    _isLoading = true;
    _error = null;
    notifyListeners();
    try {
      _user = await _googleSignIn.signInSilently();
    } catch (e) {
      _error = 'Could not restore Google session.';
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  Future<bool> signInWithGoogle() async {
    _isLoading = true;
    _error = null;
    notifyListeners();
    try {
      _user = await _googleSignIn.signIn();
      if (_user == null) {
        _error = 'Google sign-in cancelled.';
        return false;
      }
      return true;
    } catch (e) {
      _error = 'Google sign-in failed. Check setup and try again.';
      return false;
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  Future<void> signOut() async {
    _isLoading = true;
    notifyListeners();
    try {
      await _googleSignIn.signOut();
      _user = null;
      _error = null;
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }
}
