import React, { useState, useEffect, createContext, useContext } from "react";
import "./App.css";
import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

// Google Maps API Key (you'll need to get this from Google Cloud Console)
const GOOGLE_MAPS_API_KEY = "YOUR_GOOGLE_MAPS_API_KEY";

// Context pour l'authentification
const AuthContext = createContext();

const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(localStorage.getItem('token'));
  const [loading, setLoading] = useState(true);
  const [notifications, setNotifications] = useState([]);

  useEffect(() => {
    if (token) {
      axios.defaults.headers.common['Authorization'] = `Bearer ${token}`;
      fetchUser();
      fetchNotifications();
      
      // Check for notifications every 30 seconds
      const notificationInterval = setInterval(fetchNotifications, 30000);
      return () => clearInterval(notificationInterval);
    } else {
      setLoading(false);
    }
  }, [token]);

  const fetchUser = async () => {
    try {
      const response = await axios.get(`${API}/auth/me`);
      setUser(response.data);
    } catch (error) {
      console.error('Erreur lors de la récupération de l\'utilisateur:', error);
      logout();
    } finally {
      setLoading(false);
    }
  };

  const fetchNotifications = async () => {
    try {
      const response = await axios.get(`${API}/notifications?unread_only=true`);
      setNotifications(response.data);
    } catch (error) {
      console.error('Erreur lors de la récupération des notifications:', error);
    }
  };

  const markNotificationRead = async (notificationId) => {
    try {
      await axios.put(`${API}/notifications/${notificationId}/read`);
      fetchNotifications();
    } catch (error) {
      console.error('Erreur lors du marquage de la notification:', error);
    }
  };

  const login = async (email, password) => {
    try {
      const response = await axios.post(`${API}/auth/login`, { email, password });
      const { token: newToken, user: userData } = response.data;
      
      localStorage.setItem('token', newToken);
      setToken(newToken);
      setUser(userData);
      axios.defaults.headers.common['Authorization'] = `Bearer ${newToken}`;
      
      return { success: true };
    } catch (error) {
      return { 
        success: false, 
        message: error.response?.data?.detail || 'Erreur de connexion' 
      };
    }
  };

  const register = async (userData) => {
    try {
      const response = await axios.post(`${API}/auth/register`, userData);
      const { token: newToken, user: newUser } = response.data;
      
      localStorage.setItem('token', newToken);
      setToken(newToken);
      setUser(newUser);
      axios.defaults.headers.common['Authorization'] = `Bearer ${newToken}`;
      
      return { success: true };
    } catch (error) {
      return { 
        success: false, 
        message: error.response?.data?.detail || 'Erreur d\'inscription' 
      };
    }
  };

  const logout = () => {
    localStorage.removeItem('token');
    setToken(null);
    setUser(null);
    setNotifications([]);
    delete axios.defaults.headers.common['Authorization'];
  };

  return (
    <AuthContext.Provider value={{ 
      user, 
      token, 
      login, 
      register, 
      logout, 
      loading, 
      notifications, 
      markNotificationRead 
    }}>
      {children}
    </AuthContext.Provider>
  );
};

const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth doit être utilisé dans un AuthProvider');
  }
  return context;
};

// Composant de notification
const NotificationBell = () => {
  const { notifications, markNotificationRead } = useAuth();
  const [showNotifications, setShowNotifications] = useState(false);

  return (
    <div className="relative">
      <button
        onClick={() => setShowNotifications(!showNotifications)}
        className="relative p-2 text-gray-600 hover:text-gray-800"
      >
        🔔
        {notifications.length > 0 && (
          <span className="absolute -top-1 -right-1 bg-red-500 text-white text-xs rounded-full h-5 w-5 flex items-center justify-center">
            {notifications.length}
          </span>
        )}
      </button>
      
      {showNotifications && (
        <div className="absolute right-0 mt-2 w-80 bg-white rounded-lg shadow-lg border z-50">
          <div className="p-3 border-b">
            <h3 className="font-semibold">Notifications</h3>
          </div>
          <div className="max-h-64 overflow-y-auto">
            {notifications.length === 0 ? (
              <p className="p-3 text-gray-500">Aucune notification</p>
            ) : (
              notifications.map((notif) => (
                <div
                  key={notif.id}
                  className="p-3 border-b hover:bg-gray-50 cursor-pointer"
                  onClick={() => markNotificationRead(notif.id)}
                >
                  <p className="font-medium text-sm">{notif.title}</p>
                  <p className="text-xs text-gray-600">{notif.message}</p>
                  <p className="text-xs text-gray-400 mt-1">
                    {new Date(notif.created_at).toLocaleString('fr-FR')}
                  </p>
                </div>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
};

// Composant Google Maps
const GoogleMap = ({ center, markers, onMarkerClick, style }) => {
  const mapRef = React.useRef(null);
  const [map, setMap] = useState(null);
  const [googleMaps, setGoogleMaps] = useState(null);

  useEffect(() => {
    const loadGoogleMaps = () => {
      if (window.google) {
        setGoogleMaps(window.google);
        return;
      }

      const script = document.createElement('script');
      script.src = `https://maps.googleapis.com/maps/api/js?key=${GOOGLE_MAPS_API_KEY}&libraries=places`;
      script.async = true;
      script.defer = true;
      script.onload = () => {
        setGoogleMaps(window.google);
      };
      document.head.appendChild(script);
    };

    loadGoogleMaps();
  }, []);

  useEffect(() => {
    if (googleMaps && mapRef.current && !map) {
      const newMap = new googleMaps.maps.Map(mapRef.current, {
        center: center,
        zoom: 12,
      });
      setMap(newMap);
    }
  }, [googleMaps, center, map]);

  useEffect(() => {
    if (map && googleMaps && markers) {
      // Clear existing markers
      map.data.forEach((feature) => {
        map.data.remove(feature);
      });

      // Add new markers
      markers.forEach((marker) => {
        const mapMarker = new googleMaps.maps.Marker({
          position: { lat: marker.lat, lng: marker.lng },
          map: map,
          title: marker.title,
          icon: marker.icon || null,
        });

        if (onMarkerClick) {
          mapMarker.addListener('click', () => onMarkerClick(marker));
        }
      });
    }
  }, [map, googleMaps, markers, onMarkerClick]);

  return <div ref={mapRef} style={style || { width: '100%', height: '400px' }} />;
};

// Composants de l'application
const Header = () => {
  const { user, logout } = useAuth();

  return (
    <header className="header">
      <div className="container mx-auto px-4 py-4 flex justify-between items-center">
        <h1 className="text-2xl font-bold text-blue-600">
          🔧 TechSupport Pro
        </h1>
        {user && (
          <div className="flex items-center space-x-4">
            <NotificationBell />
            <span className="text-gray-600">
              Bonjour, {user.name} (
              {user.user_type === 'user' ? 'Client' : 
               user.user_type === 'technician' ? 'Technicien' : 'Administrateur'})
            </span>
            <button 
              onClick={logout}
              className="bg-red-500 text-white px-4 py-2 rounded hover:bg-red-600"
            >
              Déconnexion
            </button>
          </div>
        )}
      </div>
    </header>
  );
};

const AuthForm = () => {
  const { login, register } = useAuth();
  const [isLogin, setIsLogin] = useState(true);
  const [formData, setFormData] = useState({
    email: '',
    password: '',
    name: '',
    phone: '',
    user_type: 'user',
    address: '',
    skills: [],
    hourly_rate: ''
  });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    const result = isLogin 
      ? await login(formData.email, formData.password)
      : await register(formData);

    if (!result.success) {
      setError(result.message);
    }
    setLoading(false);
  };

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
  };

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center">
      <div className="max-w-md w-full bg-white rounded-lg shadow-md p-6">
        <div className="text-center mb-6">
          <h2 className="text-3xl font-bold text-gray-900">
            🔧 TechSupport Pro
          </h2>
          <p className="mt-2 text-gray-600">
            Support IT à la demande
          </p>
        </div>

        <div className="flex mb-6">
          <button
            className={`flex-1 py-2 px-4 rounded-l-lg ${isLogin ? 'bg-blue-500 text-white' : 'bg-gray-200'}`}
            onClick={() => setIsLogin(true)}
          >
            Connexion
          </button>
          <button
            className={`flex-1 py-2 px-4 rounded-r-lg ${!isLogin ? 'bg-blue-500 text-white' : 'bg-gray-200'}`}
            onClick={() => setIsLogin(false)}
          >
            Inscription
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          {error && (
            <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded">
              {error}
            </div>
          )}

          <div>
            <label className="block text-sm font-medium text-gray-700">Email</label>
            <input
              type="email"
              name="email"
              required
              className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md"
              value={formData.email}
              onChange={handleInputChange}
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700">Mot de passe</label>
            <input
              type="password"
              name="password"
              required
              className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md"
              value={formData.password}
              onChange={handleInputChange}
            />
          </div>

          {!isLogin && (
            <>
              <div>
                <label className="block text-sm font-medium text-gray-700">Nom complet</label>
                <input
                  type="text"
                  name="name"
                  required
                  className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md"
                  value={formData.name}
                  onChange={handleInputChange}
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700">Téléphone</label>
                <input
                  type="tel"
                  name="phone"
                  required
                  className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md"
                  value={formData.phone}
                  onChange={handleInputChange}
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700">Type de compte</label>
                <select
                  name="user_type"
                  className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md"
                  value={formData.user_type}
                  onChange={handleInputChange}
                >
                  <option value="user">Client (J'ai besoin d'aide)</option>
                  <option value="technician">Technicien (Je propose mes services)</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700">Adresse</label>
                <input
                  type="text"
                  name="address"
                  className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md"
                  value={formData.address}
                  onChange={handleInputChange}
                />
              </div>

              {formData.user_type === 'technician' && (
                <div>
                  <label className="block text-sm font-medium text-gray-700">Tarif horaire (€)</label>
                  <input
                    type="number"
                    name="hourly_rate"
                    min="0"
                    step="0.01"
                    className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md"
                    value={formData.hourly_rate}
                    onChange={handleInputChange}
                  />
                </div>
              )}
            </>
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-blue-500 text-white py-2 px-4 rounded-md hover:bg-blue-600 disabled:opacity-50"
          >
            {loading ? 'Chargement...' : (isLogin ? 'Se connecter' : 'S\'inscrire')}
          </button>
        </form>
      </div>
    </div>
  );
};

const UserDashboard = () => {
  const { user } = useAuth();
  const [interventions, setInterventions] = useState([]);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [newIntervention, setNewIntervention] = useState({
    title: '',
    description: '',
    intervention_type: 'computer',
    service_type: 'remote',
    urgency: 'medium',
    budget_min: '',
    budget_max: '',
    user_address: ''
  });

  useEffect(() => {
    fetchInterventions();
    getUserLocation();
  }, []);

  const getUserLocation = () => {
    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        (position) => {
          console.log('Position obtenue:', position.coords);
        },
        (error) => {
          console.log('Erreur de géolocalisation:', error);
        }
      );
    }
  };

  const fetchInterventions = async () => {
    try {
      const response = await axios.get(`${API}/interventions`);
      setInterventions(response.data);
    } catch (error) {
      console.error('Erreur lors de la récupération des interventions:', error);
    }
  };

  const handleCreateIntervention = async (e) => {
    e.preventDefault();
    try {
      await axios.post(`${API}/interventions`, newIntervention);
      setShowCreateForm(false);
      setNewIntervention({
        title: '',
        description: '',
        intervention_type: 'computer',
        service_type: 'remote',
        urgency: 'medium',
        budget_min: '',
        budget_max: '',
        user_address: ''
      });
      fetchInterventions();
    } catch (error) {
      console.error('Erreur lors de la création de l\'intervention:', error);
    }
  };

  const handlePayment = async (interventionId) => {
    try {
      const originUrl = window.location.origin;
      const response = await axios.post(`${API}/payments/checkout/session`, {
        intervention_id: interventionId
      }, {
        params: { origin_url: originUrl }
      });
      
      if (response.data.url) {
        window.location.href = response.data.url;
      }
    } catch (error) {
      console.error('Erreur lors de la création de la session de paiement:', error);
      alert('Erreur lors de la création du paiement');
    }
  };

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-3xl font-bold text-gray-900">Mes demandes d'intervention</h2>
        <button
          onClick={() => setShowCreateForm(true)}
          className="bg-blue-500 text-white px-6 py-2 rounded-lg hover:bg-blue-600"
        >
          + Nouvelle demande
        </button>
      </div>

      {showCreateForm && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white p-6 rounded-lg max-w-md w-full max-h-screen overflow-y-auto">
            <h3 className="text-xl font-bold mb-4">Nouvelle demande d'intervention</h3>
            <form onSubmit={handleCreateIntervention} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700">Titre</label>
                <input
                  type="text"
                  required
                  className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md"
                  value={newIntervention.title}
                  onChange={(e) => setNewIntervention({...newIntervention, title: e.target.value})}
                  placeholder="Ex: Réparation ordinateur portable"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700">Description</label>
                <textarea
                  required
                  rows="3"
                  className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md"
                  value={newIntervention.description}
                  onChange={(e) => setNewIntervention({...newIntervention, description: e.target.value})}
                  placeholder="Décrivez votre problème en détail..."
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700">Type d'appareil</label>
                <select
                  className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md"
                  value={newIntervention.intervention_type}
                  onChange={(e) => setNewIntervention({...newIntervention, intervention_type: e.target.value})}
                >
                  <option value="computer">Ordinateur</option>
                  <option value="phone">Téléphone</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700">Type de service</label>
                <select
                  className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md"
                  value={newIntervention.service_type}
                  onChange={(e) => setNewIntervention({...newIntervention, service_type: e.target.value})}
                >
                  <option value="remote">À distance</option>
                  <option value="onsite">Sur site</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700">Urgence</label>
                <select
                  className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md"
                  value={newIntervention.urgency}
                  onChange={(e) => setNewIntervention({...newIntervention, urgency: e.target.value})}
                >
                  <option value="low">Basse</option>
                  <option value="medium">Moyenne</option>
                  <option value="high">Haute</option>
                </select>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700">Budget min (€)</label>
                  <input
                    type="number"
                    min="0"
                    step="0.01"
                    required
                    className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md"
                    value={newIntervention.budget_min}
                    onChange={(e) => setNewIntervention({...newIntervention, budget_min: e.target.value})}
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700">Budget max (€)</label>
                  <input
                    type="number"
                    min="0"
                    step="0.01"
                    required
                    className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md"
                    value={newIntervention.budget_max}
                    onChange={(e) => setNewIntervention({...newIntervention, budget_max: e.target.value})}
                  />
                </div>
              </div>

              {newIntervention.service_type === 'onsite' && (
                <div>
                  <label className="block text-sm font-medium text-gray-700">Adresse d'intervention</label>
                  <input
                    type="text"
                    className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md"
                    value={newIntervention.user_address}
                    onChange={(e) => setNewIntervention({...newIntervention, user_address: e.target.value})}
                    placeholder="Adresse complète..."
                  />
                </div>
              )}

              <div className="flex space-x-4">
                <button
                  type="submit"
                  className="flex-1 bg-blue-500 text-white py-2 px-4 rounded-md hover:bg-blue-600"
                >
                  Créer la demande
                </button>
                <button
                  type="button"
                  onClick={() => setShowCreateForm(false)}
                  className="flex-1 bg-gray-300 text-gray-700 py-2 px-4 rounded-md hover:bg-gray-400"
                >
                  Annuler
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      <div className="grid gap-6">
        {interventions.map((intervention) => (
          <div key={intervention.id} className="bg-white p-6 rounded-lg shadow-md border">
            <div className="flex justify-between items-start mb-4">
              <div>
                <h3 className="text-xl font-semibold text-gray-900">{intervention.title}</h3>
                <p className="text-gray-600 mt-1">{intervention.description}</p>
              </div>
              <span className={`px-3 py-1 rounded-full text-sm font-medium ${
                intervention.status === 'pending' ? 'bg-yellow-100 text-yellow-800' :
                intervention.status === 'assigned' ? 'bg-blue-100 text-blue-800' :
                intervention.status === 'in_progress' ? 'bg-purple-100 text-purple-800' :
                intervention.status === 'completed' ? 'bg-green-100 text-green-800' :
                'bg-red-100 text-red-800'
              }`}>
                {intervention.status === 'pending' ? 'En attente' :
                 intervention.status === 'assigned' ? 'Assignée' :
                 intervention.status === 'in_progress' ? 'En cours' :
                 intervention.status === 'completed' ? 'Terminée' : 'Annulée'}
              </span>
            </div>

            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm text-gray-600 mb-4">
              <div>
                <span className="font-medium">Type:</span> {
                  intervention.intervention_type === 'computer' ? 'Ordinateur' : 'Téléphone'
                }
              </div>
              <div>
                <span className="font-medium">Service:</span> {
                  intervention.service_type === 'remote' ? 'À distance' : 'Sur site'
                }
              </div>
              <div>
                <span className="font-medium">Urgence:</span> {
                  intervention.urgency === 'low' ? 'Basse' :
                  intervention.urgency === 'medium' ? 'Moyenne' : 'Haute'
                }
              </div>
              <div>
                <span className="font-medium">Budget:</span> {intervention.budget_min}€ - {intervention.budget_max}€
              </div>
            </div>

            {intervention.final_price && intervention.status === 'assigned' && (
              <div className="bg-green-50 p-4 rounded-lg mb-4">
                <p className="text-green-800 font-medium">
                  Prix final proposé: {intervention.final_price}€
                </p>
                <button
                  onClick={() => handlePayment(intervention.id)}
                  className="mt-2 bg-green-500 text-white px-4 py-2 rounded hover:bg-green-600"
                >
                  Payer maintenant
                </button>
              </div>
            )}

            <div className="text-xs text-gray-500">
              Créée le {new Date(intervention.created_at).toLocaleDateString('fr-FR')}
            </div>
          </div>
        ))}
      </div>

      {interventions.length === 0 && (
        <div className="text-center py-12">
          <p className="text-gray-500 text-lg">Aucune demande d'intervention pour le moment</p>
          <p className="text-gray-400">Créez votre première demande pour commencer</p>
        </div>
      )}
    </div>
  );
};

const TechnicianDashboard = () => {
  const { user } = useAuth();
  const [interventions, setInterventions] = useState([]);
  const [available, setAvailable] = useState(user?.available || false);

  useEffect(() => {
    fetchInterventions();
    getUserLocation();
  }, []);

  const getUserLocation = () => {
    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        (position) => {
          console.log('Position technicien obtenue:', position.coords);
          // TODO: Mettre à jour la position du technicien en base
        },
        (error) => {
          console.log('Erreur de géolocalisation:', error);
        }
      );
    }
  };

  const fetchInterventions = async () => {
    try {
      const response = await axios.get(`${API}/interventions`);
      setInterventions(response.data);
    } catch (error) {
      console.error('Erreur lors de la récupération des interventions:', error);
    }
  };

  const toggleAvailability = async () => {
    try {
      await axios.put(`${API}/technicians/availability`, { available: !available });
      setAvailable(!available);
    } catch (error) {
      console.error('Erreur lors de la mise à jour de la disponibilité:', error);
    }
  };

  const acceptIntervention = async (interventionId) => {
    try {
      await axios.put(`${API}/interventions/${interventionId}/assign`);
      fetchInterventions();
    } catch (error) {
      console.error('Erreur lors de l\'acceptation de l\'intervention:', error);
    }
  };

  const updateStatus = async (interventionId, status, finalPrice = null) => {
    try {
      const data = { new_status: status };
      if (finalPrice) {
        data.final_price = parseFloat(finalPrice);
      }
      await axios.put(`${API}/interventions/${interventionId}/status`, data);
      fetchInterventions();
    } catch (error) {
      console.error('Erreur lors de la mise à jour du statut:', error);
    }
  };

  const availableInterventions = interventions.filter(i => i.status === 'pending');
  const myInterventions = interventions.filter(i => i.technician_id === user?.id);

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-3xl font-bold text-gray-900">Tableau de bord Technicien</h2>
        <div className="flex items-center space-x-4">
          <span className="text-gray-600">Disponible:</span>
          <button
            onClick={toggleAvailability}
            className={`px-4 py-2 rounded-lg font-medium ${
              available 
                ? 'bg-green-500 text-white hover:bg-green-600' 
                : 'bg-gray-500 text-white hover:bg-gray-600'
            }`}
          >
            {available ? 'Oui' : 'Non'}
          </button>
        </div>
      </div>

      <div className="grid md:grid-cols-2 gap-8">
        {/* Interventions disponibles */}
        <div>
          <h3 className="text-xl font-semibold mb-4">
            Interventions disponibles ({availableInterventions.length})
          </h3>
          <div className="space-y-4">
            {availableInterventions.map((intervention) => (
              <div key={intervention.id} className="bg-white p-4 rounded-lg shadow-md border">
                <h4 className="font-semibold text-gray-900">{intervention.title}</h4>
                <p className="text-gray-600 text-sm mt-1">{intervention.description}</p>
                
                <div className="grid grid-cols-2 gap-2 text-xs text-gray-500 mt-3">
                  <div>Type: {intervention.intervention_type === 'computer' ? 'Ordinateur' : 'Téléphone'}</div>
                  <div>Service: {intervention.service_type === 'remote' ? 'À distance' : 'Sur site'}</div>
                  <div>Urgence: {
                    intervention.urgency === 'low' ? 'Basse' :
                    intervention.urgency === 'medium' ? 'Moyenne' : 'Haute'
                  }</div>
                  <div>Budget: {intervention.budget_min}€ - {intervention.budget_max}€</div>
                </div>

                <button
                  onClick={() => acceptIntervention(intervention.id)}
                  className="mt-3 w-full bg-blue-500 text-white py-2 px-4 rounded hover:bg-blue-600"
                >
                  Accepter cette intervention
                </button>
              </div>
            ))}
            
            {availableInterventions.length === 0 && (
              <p className="text-gray-500 text-center py-8">
                Aucune intervention disponible pour le moment
              </p>
            )}
          </div>
        </div>

        {/* Mes interventions */}
        <div>
          <h3 className="text-xl font-semibold mb-4">
            Mes interventions ({myInterventions.length})
          </h3>
          <div className="space-y-4">
            {myInterventions.map((intervention) => (
              <div key={intervention.id} className="bg-white p-4 rounded-lg shadow-md border">
                <div className="flex justify-between items-start mb-2">
                  <h4 className="font-semibold text-gray-900">{intervention.title}</h4>
                  <span className={`px-2 py-1 rounded text-xs font-medium ${
                    intervention.status === 'assigned' ? 'bg-blue-100 text-blue-800' :
                    intervention.status === 'in_progress' ? 'bg-purple-100 text-purple-800' :
                    'bg-green-100 text-green-800'
                  }`}>
                    {intervention.status === 'assigned' ? 'Assignée' :
                     intervention.status === 'in_progress' ? 'En cours' : 'Terminée'}
                  </span>
                </div>
                
                <p className="text-gray-600 text-sm">{intervention.description}</p>
                
                <div className="text-xs text-gray-500 mt-2">
                  Budget: {intervention.budget_min}€ - {intervention.budget_max}€
                </div>

                {intervention.status === 'assigned' && (
                  <div className="mt-3 space-y-2">
                    <input
                      type="number"
                      placeholder="Prix final (€)"
                      step="0.01"
                      min="0"
                      className="w-full px-3 py-2 border border-gray-300 rounded text-sm"
                      id={`price-${intervention.id}`}
                    />
                    <button
                      onClick={() => {
                        const priceInput = document.getElementById(`price-${intervention.id}`);
                        const price = priceInput.value;
                        if (price) {
                          updateStatus(intervention.id, 'assigned', price);
                        }
                      }}
                      className="w-full bg-green-500 text-white py-2 px-4 rounded text-sm hover:bg-green-600"
                    >
                      Proposer ce prix
                    </button>
                  </div>
                )}

                {intervention.status === 'in_progress' && (
                  <button
                    onClick={() => updateStatus(intervention.id, 'completed')}
                    className="mt-3 w-full bg-green-500 text-white py-2 px-4 rounded text-sm hover:bg-green-600"
                  >
                    Marquer comme terminée
                  </button>
                )}
              </div>
            ))}
            
            {myInterventions.length === 0 && (
              <p className="text-gray-500 text-center py-8">
                Aucune intervention acceptée pour le moment
              </p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

const PaymentSuccess = () => {
  const [sessionId, setSessionId] = useState(null);
  const [paymentStatus, setPaymentStatus] = useState('checking');

  useEffect(() => {
    const urlParams = new URLSearchParams(window.location.search);
    const id = urlParams.get('session_id');
    if (id) {
      setSessionId(id);
      checkPaymentStatus(id);
    }
  }, []);

  const checkPaymentStatus = async (id, attempts = 0) => {
    const maxAttempts = 5;
    try {
      const response = await axios.get(`${API}/payments/checkout/status/${id}`);
      if (response.data.payment_status === 'paid') {
        setPaymentStatus('success');
      } else if (response.data.status === 'expired') {
        setPaymentStatus('expired');
      } else if (attempts < maxAttempts) {
        setTimeout(() => checkPaymentStatus(id, attempts + 1), 2000);
      } else {
        setPaymentStatus('timeout');
      }
    } catch (error) {
      console.error('Erreur lors de la vérification du paiement:', error);
      setPaymentStatus('error');
    }
  };

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="max-w-md mx-auto bg-white p-6 rounded-lg shadow-md text-center">
        {paymentStatus === 'checking' && (
          <>
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto mb-4"></div>
            <h2 className="text-xl font-semibold mb-2">Vérification du paiement...</h2>
            <p className="text-gray-600">Veuillez patienter</p>
          </>
        )}
        
        {paymentStatus === 'success' && (
          <>
            <div className="text-green-500 text-6xl mb-4">✓</div>
            <h2 className="text-xl font-semibold mb-2 text-green-600">Paiement réussi !</h2>
            <p className="text-gray-600 mb-4">Votre paiement a été traité avec succès</p>
            <a 
              href="/interventions"
              className="bg-blue-500 text-white px-4 py-2 rounded hover:bg-blue-600"
            >
              Retour à mes interventions
            </a>
          </>
        )}
        
        {paymentStatus === 'expired' && (
          <>
            <div className="text-red-500 text-6xl mb-4">⚠</div>
            <h2 className="text-xl font-semibold mb-2 text-red-600">Session expirée</h2>
            <p className="text-gray-600 mb-4">Votre session de paiement a expiré</p>
            <a 
              href="/interventions"
              className="bg-blue-500 text-white px-4 py-2 rounded hover:bg-blue-600"
            >
              Réessayer
            </a>
          </>
        )}
        
        {(paymentStatus === 'error' || paymentStatus === 'timeout') && (
          <>
            <div className="text-red-500 text-6xl mb-4">⚠</div>
            <h2 className="text-xl font-semibold mb-2 text-red-600">Erreur</h2>
            <p className="text-gray-600 mb-4">Impossible de vérifier le statut du paiement</p>
            <a 
              href="/interventions"
              className="bg-blue-500 text-white px-4 py-2 rounded hover:bg-blue-600"
            >
              Retour
            </a>
          </>
        )}
      </div>
    </div>
  );
};

const App = () => {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
      </div>
    );
  }

  // Routing simple basé sur l'URL
  const path = window.location.pathname;

  if (!user) {
    return <AuthForm />;
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <Header />
      {path === '/payment-success' ? (
        <PaymentSuccess />
      ) : user.user_type === 'user' ? (
        <UserDashboard />
      ) : (
        <TechnicianDashboard />
      )}
    </div>
  );
};

const AppWithAuth = () => {
  return (
    <AuthProvider>
      <App />
    </AuthProvider>
  );
};

export default AppWithAuth;