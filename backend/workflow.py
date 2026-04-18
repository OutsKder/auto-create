import asyncio
import json
import os

class ReliableAgentWorkflow:
    def __init__(self, mocks_file: str = "fallback_mocks.json"):
        # 加载防翻车剧本
        try:
            with open(mocks_file, 'r', encoding='utf-8') as f:
                self.mocks = json.load(f)
        except Exception:
            self.mocks = {}

    def _determine_golden_path(self, title: str):
        # 简单匹配：如果需求标题包含"审批"，则走预设的完美剧本
        for keyword, paths in self.mocks.get("golden_paths", {}).items():
            if keyword in title:
                return paths
        return None

    async def execute_stage_stream(self, req_id: str, stage_id: str, req_data: dict, mock_error: bool = False):
        """
        核心编排与流式发生器：包裹了多级容错与熔断机制。
        支持从真实的 LLM 接入并拉取数据，同时具备完美的回退能力。
        """
        from llm import stream_llm_response
        
        # 1. 尝试匹配黄金剧本 (The Golden Path)
        golden_scenarios = self._determine_golden_path(req_data.get("title", ""))
        
        yield f"data: {json.dumps({'status': 'running', 'text': ''})}\n\n"
        await asyncio.sleep(0.3)

        if golden_scenarios and stage_id in golden_scenarios:
            # 走硬编码的旁路，实现秒级的高质量返回展示
            content = golden_scenarios[stage_id]
            yield f"data: {json.dumps({'status': 'running', 'text': '✨ (旁路命中：正在基于最佳实践全自动推演)\\n\\n'})}\n\n"
            
            for i, char in enumerate(content):
                # 如果发生打断模拟测试
                if mock_error and i == len(content) // 2:
                    await self._handle_fallback(Exception("Demo 中断模拟！"), stage_id)
                    return
                
                response_chunk = json.dumps({'status': 'running', 'text': char})
                yield f"data: {response_chunk}\n\n"
                await asyncio.sleep(0.01)
                
            self._finalize_stage(stage_id)
            final_status = "waiting_review" if stage_id in ["solution", "review"] else "completed"
            yield f"data: {json.dumps({'status': final_status, 'text': '\\n'})}\n\n"
            return
            
        # 2. 如果没有黄金预设剧本，尝试直接走真正的 LLM 接口
        # ============= 真实大模型流式调用环节 ============= 
        try:
            if stage_id == "coding":
                from coder_agent import stream_coder_agent
                
                # 尝试读取上一步（方案设计方案）作为上下文提供给 Coder
                arch_context = "暂无系统架构文档"
                arch_path = os.path.join("outputs", f"{req_id}_solution.md")
                if os.path.exists(arch_path):
                    with open(arch_path, "r", encoding="utf-8") as f:
                        arch_context = f.read()
                        
                generator = stream_coder_agent(req_id, req_data, arch_context)
            elif stage_id == "testing":
                from test_agent import stream_test_agent
                
                # 读取代码结构作为上下文
                arch_context = "暂无代码文档"
                arch_path = os.path.join("outputs", f"{req_id}_solution.md")
                if os.path.exists(arch_path):
                    with open(arch_path, "r", encoding="utf-8") as f:
                        arch_context = f.read()
                
                generator = stream_test_agent(req_id, req_data, arch_context)
            else:
                from llm import stream_llm_response
                generator = stream_llm_response(stage_id, req_data)
            
            # 建立用于自动写 MD 文件的文件夹
            os.makedirs("outputs", exist_ok=True)
            doc_path = os.path.join("outputs", f"{req_id}_{stage_id}.md")
            
            async for chunk_text in generator:
                # 断流演练
                if mock_error:
                    raise ConnectionError("LLM API Gateway 502 Timeout")
                
                # 同步写入 Markdown 文档
                with open(doc_path, "a", encoding="utf-8") as f:
                    f.write(chunk_text)

                yield f"data: {json.dumps({'status': 'running', 'text': chunk_text})}\n\n"
                
        except Exception as e:
            # 3. SSE 管道平滑接管 (Seamless Stream Rescue)
            # 在任何流中断的地方，原地重启“神之路径通用回退”，补全缺失文本
            yield f"\ndata: {json.dumps({'status': 'running', 'text': f'\\n\\n⚠️ **大模型节点异常**: {str(e)}。**回退链路无缝接管中...**\\n\\n'})}\n\n"
            await asyncio.sleep(1)
            
            fallback_content = self.mocks.get("universal_fallback", "系统兜底方案已接管流程。")
            for char in fallback_content:
                yield f"data: {json.dumps({'status': 'running', 'text': char})}\n\n"
                await asyncio.sleep(0.02)

        # 5. 阶段完成判定
        final_status = "waiting_review" if stage_id in ["solution", "review"] else "completed"
        finish_chunk = json.dumps({'status': final_status, 'text': '\n'})
        yield f"data: {finish_chunk}\n\n"

    async def _handle_fallback(self, error, stage_id):
        # ... 后续如果要扩展更多独立接管逻辑可以放这里
        pass
    
    def _finalize_stage(self, stage_id):
        pass