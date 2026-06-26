import { useState, useRef } from 'react';
import { UploadCloud, CheckCircle, AlertTriangle, XCircle, FileIcon, Loader2, Camera } from 'lucide-react';
import './index.css';

function App() {
  const [file, setFile] = useState(null);
  const [docType, setDocType] = useState('ITR/Form 16');
  const [method, setMethod] = useState('Government Database');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [showCamera, setShowCamera] = useState(false);
  
  const fileInputRef = useRef(null);
  const videoRef = useRef(null);
  const canvasRef = useRef(null);

  const handleFileSelect = (e) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
    }
  };

  const startCamera = async () => {
    setShowCamera(true);
    try {
      // Use 'ideal' so desktop webcams aren't rejected for not being 'environment' (rear) cameras
      const stream = await navigator.mediaDevices.getUserMedia({ 
        video: { facingMode: { ideal: 'environment' } } 
      });
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        videoRef.current.play();
      }
    } catch (err) {
      console.error("Error accessing camera:", err);
      alert("Could not access camera. Make sure no other app is using it, and permissions are granted.");
      setShowCamera(false);
    }
  };

  const stopCamera = () => {
    if (videoRef.current && videoRef.current.srcObject) {
      const tracks = videoRef.current.srcObject.getTracks();
      tracks.forEach(track => track.stop());
    }
    setShowCamera(false);
  };

  const capturePhoto = (e) => {
    e.stopPropagation();
    if (videoRef.current && canvasRef.current) {
      const video = videoRef.current;
      const canvas = canvasRef.current;
      canvas.width = video.videoWidth;
      canvas.height = video.videoHeight;
      const ctx = canvas.getContext('2d');
      ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
      
      canvas.toBlob((blob) => {
        const newFile = new File([blob], "camera-capture.jpg", { type: "image/jpeg" });
        setFile(newFile);
        stopCamera();
      }, "image/jpeg", 0.9);
    }
  };

  const handleVerify = async () => {
    if (!file) {
      alert('Please select a file first.');
      return;
    }

    setLoading(true);
    setResult(null);

    const formData = new FormData();
    formData.append('file', file);
    formData.append('document_type', docType);
    formData.append('verification_method', method);

    try {
      const response = await fetch('http://localhost:8000/api/v1/verify/orchestrate', {
        method: 'POST',
        body: formData,
      });
      
      const data = await response.json();
      setResult(data);
    } catch (error) {
      console.error('Verification failed:', error);
      setResult({
        bucket: 3,
        status: 'Error',
        description: 'Failed to connect to the backend server. Is it running?',
        differences: [error.message]
      });
    } finally {
      setLoading(false);
    }
  };

  const getStatusIcon = (bucket) => {
    switch (bucket) {
      case 1: return <CheckCircle size={24} />;
      case 2: return <AlertTriangle size={24} />;
      default: return <XCircle size={24} />;
    }
  };

  const getStatusClass = (bucket) => {
    switch (bucket) {
      case 1: return 'status-success';
      case 2: return 'status-warning';
      default: return 'status-error';
    }
  };

  return (
    <div className="app-container">
      <header className="header">
        <h1>Suraksha Drishti</h1>
        <p>Intelligent Document Verification & Forensics</p>
      </header>

      <div className="grid-layout">
        {/* Left Column: Input Controls */}
        <div className="glass-panel">
          <div className="controls-section">
            <div 
              className={`upload-area ${(file && !showCamera) ? 'active' : ''}`}
              onClick={() => {
                if (!showCamera) fileInputRef.current?.click();
              }}
            >
              <input 
                type="file" 
                ref={fileInputRef}
                onChange={handleFileSelect}
                accept="image/*,application/pdf"
                style={{ display: 'none' }}
              />
              
              {showCamera ? (
                <div className="camera-view" onClick={(e) => e.stopPropagation()}>
                  <video ref={videoRef} autoPlay playsInline muted />
                  <canvas ref={canvasRef} style={{ display: 'none' }} />
                  <div className="camera-controls">
                    <button className="close-camera-btn" onClick={(e) => { e.stopPropagation(); stopCamera(); }}>
                      <XCircle size={24} />
                    </button>
                    <button className="capture-btn" onClick={capturePhoto}>
                      <Camera size={24} />
                    </button>
                  </div>
                </div>
              ) : file ? (
                <>
                  <FileIcon size={48} />
                  <div className="file-name-display">
                    {file.name}
                  </div>
                  <button 
                    onClick={(e) => { e.stopPropagation(); setFile(null); }}
                    style={{ background: 'transparent', border: '1px solid var(--border-glass)', color: 'white', padding: '0.5rem 1rem', borderRadius: '20px', cursor: 'pointer', marginTop: '1rem' }}
                  >
                    Clear Selection
                  </button>
                </>
              ) : (
                <>
                  <UploadCloud size={48} />
                  <div className="upload-text">
                    <span>Click to upload</span> or drag and drop<br/>
                    PDF, PNG, or JPEG
                  </div>
                  <div 
                    onClick={(e) => { e.stopPropagation(); startCamera(); }}
                    style={{ marginTop: '1rem', color: 'var(--accent-primary)', cursor: 'pointer', padding: '0.5rem 1rem', background: 'rgba(59, 130, 246, 0.1)', borderRadius: '10px', transition: 'all 0.2s' }}
                  >
                    <Camera size={24} style={{ margin: '0 auto 0.5rem auto', display: 'block' }} />
                    <small style={{ fontWeight: '500' }}>Open Live Camera</small>
                  </div>
                </>
              )}
            </div>

            <div className="input-group">
              <label>Document Type</label>
              <select 
                className="select-input" 
                value={docType}
                onChange={(e) => setDocType(e.target.value)}
              >
                <option value="ITR/Form 16">ITR / Form 16</option>
                <option value="Udyam Certificate">Udyam Certificate</option>
                <option value="Trade Licence">Trade Licence</option>
                <option value="GST Registration">GST Registration</option>
                <option value="Salary Slip">Salary Slip</option>
              </select>
            </div>

            <div className="input-group">
              <label>Verification Method</label>
              <div className="radio-group">
                <label className={`radio-option ${method === 'Government Database' ? 'selected' : ''}`}>
                  <input 
                    type="radio" 
                    name="method" 
                    value="Government Database"
                    checked={method === 'Government Database'}
                    onChange={(e) => setMethod(e.target.value)}
                    style={{ display: 'none' }}
                  />
                  <div style={{ display: 'flex', flexDirection: 'column' }}>
                    <strong>Government Database</strong>
                    <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>Cross-check with live government portals</span>
                  </div>
                </label>
                <label className={`radio-option ${method === 'Forensic Analysis' ? 'selected' : ''}`}>
                  <input 
                    type="radio" 
                    name="method" 
                    value="Forensic Analysis"
                    checked={method === 'Forensic Analysis'}
                    onChange={(e) => setMethod(e.target.value)}
                    style={{ display: 'none' }}
                  />
                  <div style={{ display: 'flex', flexDirection: 'column' }}>
                    <strong>DNA Forensic Analysis</strong>
                    <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>Detect image manipulation & math forgery</span>
                  </div>
                </label>
              </div>
            </div>

            <button 
              className="verify-btn"
              onClick={handleVerify}
              disabled={!file || loading}
            >
              {loading ? (
                <><Loader2 className="loading-spinner" /> Processing Document...</>
              ) : (
                'Scan & Verify'
              )}
            </button>
          </div>
        </div>

        {/* Right Column: Results */}
        <div className="glass-panel" style={{ display: 'flex', flexDirection: 'column', justifyContent: result ? 'flex-start' : 'center' }}>
          {!result && !loading && (
            <div style={{ textAlign: 'center', color: 'var(--text-secondary)' }}>
              <CheckCircle size={64} style={{ opacity: 0.2, marginBottom: '1rem' }} />
              <h3>Awaiting Document</h3>
              <p>Upload a document and click verify to see results.</p>
            </div>
          )}

          {loading && (
            <div style={{ textAlign: 'center', color: 'var(--accent-primary)' }}>
              <Loader2 size={64} className="loading-spinner" style={{ marginBottom: '1rem' }} />
              <h3>Analyzing...</h3>
              <p style={{ color: 'var(--text-secondary)' }}>Extracting DNA and cross-referencing databases.</p>
            </div>
          )}

          {result && !loading && (
            <div className="results-dashboard">
              <div className="result-header">
                <div className={`status-badge ${getStatusClass(result.bucket)}`}>
                  {getStatusIcon(result.bucket)}
                  {result.status}
                </div>
                <div className="bucket-indicator">
                  Bucket {result.bucket}
                </div>
              </div>

              <div className="description-text">
                {result.description}
              </div>

              {result.differences && result.differences.length > 0 && (
                <div className="differences-list">
                  <h4><AlertTriangle size={18} /> Discrepancies Found</h4>
                  <ul>
                    {result.differences.map((diff, index) => (
                      <li key={index}>{diff}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default App;
