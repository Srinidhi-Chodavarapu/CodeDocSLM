import axios, { AxiosInstance } from 'axios';
import FormData from 'form-data';
import {
    GenerateDocRequest,
    GenerateDocResponse,
    GenerateFileResponse,
    GenerateProjectResponse,
    HealthResponse,
    InfoResponse
} from './types';

export class ApiClient {
    private client: AxiosInstance;
    private baseUrl: string;
    private infoCache: InfoResponse | null = null;

    constructor(port: number) {
        this.baseUrl = `http://localhost:${port}`;
        this.client = axios.create({
            baseURL: this.baseUrl,
            timeout: 300000, // 5 minutes for large operations
            headers: {
                'Content-Type': 'application/json'
            }
        });
    }

    async health(): Promise<HealthResponse> {
        const response = await this.client.get<HealthResponse>('/health');
        return response.data;
    }

    async info(useCache: boolean = true): Promise<InfoResponse> {
        if (useCache && this.infoCache) {
            return this.infoCache;
        }
        
        const response = await this.client.get<InfoResponse>('/info');
        this.infoCache = response.data;
        return response.data;
    }

    async generateDoc(request: GenerateDocRequest): Promise<GenerateDocResponse> {
        const response = await this.client.post<GenerateDocResponse>('/generate/doc', request);
        return response.data;
    }

    async generateFile(file: Buffer, filename: string): Promise<GenerateFileResponse> {
        const formData = new FormData();
        formData.append('file', file, filename);

        const response = await this.client.post<GenerateFileResponse>(
            '/generate/file',
            formData,
            {
                headers: {
                    ...formData.getHeaders()
                }
            }
        );
        return response.data;
    }

    async generateProject(zipBuffer: Buffer, writeBack: boolean = false): Promise<GenerateProjectResponse | Buffer> {
        const formData = new FormData();
        formData.append('file', zipBuffer, 'project.zip');
        formData.append('write_back', writeBack.toString());

        const response = await this.client.post(
            '/generate/project',
            formData,
            {
                headers: {
                    ...formData.getHeaders()
                },
                responseType: writeBack ? 'arraybuffer' : 'json'
            }
        );

        if (writeBack) {
            return Buffer.from(response.data);
        }
        return response.data as GenerateProjectResponse;
    }

    clearCache(): void {
        this.infoCache = null;
    }

    getBaseUrl(): string {
        return this.baseUrl;
    }
}
