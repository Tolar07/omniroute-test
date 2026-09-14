import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  Button,
  FlatList,
  TouchableOpacity,
  ScrollView,
  ActivityIndicator,
  StyleSheet,
  Alert,
  Platform
} from 'react-native';

// Configuration
const SERVER_IP = '192.168.68.105'; // Replace with actual IP from ipconfig
const SERVER_PORT = 5000;
const BASE_URL = `http://${SERVER_IP}:${SERVER_PORT}`;

export default function App() {
  const [boards, setBoards] = useState([]);
  const [selectedBoard, setSelectedBoard] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [runStatus, setRunStatus] = useState({
    inProgress: false,
    log: '',
    isFetching: false
  });

  // Fetch boards (last 14 days)
  const fetchBoards = async () => {
    setIsLoading(true);
    try {
      const response = await fetch(`${BASE_URL}/boards`);
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      const data = await response.json();
      setBoards(data.boards);
    } catch (error) {
      console.error('Error fetching boards:', error);
      Alert.alert('Error', 'Failed to fetch boards. Make sure the server is running and IP is correct.');
    } finally {
      setIsLoading(false);
    }
  };

  // Fetch board content for a specific date
  const fetchBoardContent = async (date) => {
    setIsLoading(true);
    try {
      const response = await fetch(`${BASE_URL}/boards/${date}`);
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      const data = await response.json();
      setSelectedBoard(data.content);
    } catch (error) {
      console.error('Error fetching board content:', error);
      Alert.alert('Error', 'Failed to fetch board content.');
    } finally {
      setIsLoading(false);
    }
  };

  // Start pipeline run
  const startRun = async () => {
    setRunStatus(prev => ({ ...prev, isFetching: true }));
    try {
      const response = await fetch(`${BASE_URL}/run`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      // Start polling for status
      pollRunStatus();
    } catch (error) {
      console.error('Error starting run:', error);
      Alert.alert('Error', error.message || 'Failed to start pipeline run');
    } finally {
      setRunStatus(prev => ({ ...prev, isFetching: false }));
    }
  };

  // Poll run status
  const pollRunStatus = async () => {
    setRunStatus(prev => ({ ...prev, inProgress: true, log: 'Checking status...' }));

    try {
      const response = await fetch(`${BASE_URL}/run/status`);
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      const data = await response.json();

      setRunStatus(prev => ({
        ...prev,
        inProgress: data.in_progress,
        log: data.log || '',
        isFetching: false
      }));

      // If still in progress, continue polling
      if (data.in_progress) {
        setTimeout(pollRunStatus, 1500); // Poll every 1.5 seconds
      } else {
        // Run completed, refresh boards
        setTimeout(fetchBoards, 1000);
      }
    } catch (error) {
      console.error('Error checking run status:', error);
      setRunStatus(prev => ({
        ...prev,
        inProgress: false,
        log: 'Error checking status',
        isFetching: false
      }));
      Alert.alert('Error', 'Failed to check pipeline status');
    }
  };

  // Refresh boards when returning from board view
  useEffect(() => {
    if (!selectedBoard) {
      fetchBoards();
    }
  }, [selectedBoard]);

  // Initial load
  useEffect(() => {
    fetchBoards();
  }, []);

  if (isLoading && boards.length === 0 && !selectedBoard) {
    return (
      <View style={styles.container}>
        <ActivityIndicator size="large" color="#0000ff" />
        <Text>Loading boards...</Text>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      {selectedBoard ? (
        <View style={styles.boardView}>
          <Text style={styles.header}>OLP XDV Board - {selectedBoard.split('\n')[0] || 'Today'}</Text>
          <Button title="← Back to Boards" onPress={() => setSelectedBoard(null)} />
          <ScrollView style={styles.scrollView}>
            <Text style={styles.boardText}>{selectedBoard}</Text>
          </ScrollView>
        </View>
      ) : (
        <View style={styles.container}>
          <Text style={styles.title}>OLP XDV Mobile</Text>
          {/* Run Pipeline Button */}
          <View style={styles.buttonContainer}>
            <Button
              title="Run Today's Pipeline"
              onPress={startRun}
              disabled={runStatus.inProgress || runStatus.isFetching}
            />
            {runStatus.isFetching && (
              <Text style={styles.statusText}>Checking server...</Text>
            )}
            {runStatus.inProgress && (
              <Text style={styles.statusText}>Pipeline running...</Text>
            )}
          </View>

          {/* Run Status Log */}
          {runStatus.log && runStatus.log !== 'Checking status...' && runStatus.log !== 'Pipeline running...' && (
            <View style={styles.logContainer}>
              <Text style={styles.logHeader}>Pipeline Log:</Text>
              <ScrollView style={styles.logScroll}>
                <Text style={styles.logText}>{runStatus.log}</Text>
              </ScrollView>
            </View>
          )}

          {/* Boards List */}
          <Text style={styles.sectionTitle}>Recent Boards (Last 14 Days)</Text>
          {boards.length === 0 ? (
            <Text style={styles.emptyText}>No boards available</Text>
          ) : (
            <FlatList
              data={boards}
              keyExtractor={item => item}
              renderItem={({ item }) => (
                <TouchableOpacity
                  style={styles.boardItem}
                  onPress={() => fetchBoardContent(item)}
                >
                  <Text style={styles.boardItemText}>{item}</Text>
                </TouchableOpacity>
              )}
            />
          )}
        </View>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    padding: 20,
    backgroundColor: '#f5f5f5',
  },
  boardView: {
    flex: 1,
    padding: 20,
  },
  header: {
    fontSize: 20,
    fontWeight: 'bold',
    marginBottom: 20,
    textAlign: 'center',
  },
  title: {
    fontSize: 24,
    fontWeight: 'bold',
    textAlign: 'center',
    marginBottom: 30,
    color: '#2c3e50',
  },
  buttonContainer: {
    marginBottom: 20,
  },
  statusText: {
    textAlign: 'center',
    marginTop: 10,
    fontStyle: 'italic',
    color: '#7f8c8d',
  },
  logContainer: {
    marginBottom: 20,
    borderWidth: 1,
    borderColor: '#ddd',
    borderRadius: 5,
    overflow: 'hidden',
  },
  logHeader: {
    fontSize: 16,
    fontWeight: 'bold',
    backgroundColor: '#ecf0f1',
    padding: 10,
  },
  logScroll: {
    maxHeight: 200,
  },
  logText: {
    fontFamily: 'monospace',
    fontSize: 12,
    lineHeight: 16,
    padding: 10,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    marginTop: 20,
    marginBottom: 10,
    color: '#34495e',
  },
  emptyText: {
    textAlign: 'center',
    color: '#95a5a6',
    fontStyle: 'italic',
    padding: 20,
  },
  boardItem: {
    padding: 15,
    backgroundColor: '#fff',
    borderRadius: 8,
    marginBottom: 10,
    elevation: 2,
  },
  boardItemText: {
    fontSize: 16,
    color: '#2c3e50',
  },
  scrollView: {
    flex: 1,
  },
  boardText: {
    fontFamily: 'monospace',
    fontSize: 14,
    lineHeight: 20,
  },
});
