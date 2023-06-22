/**
 * Autogenerated by Thrift Compiler (0.12.0)
 *
 * DO NOT EDIT UNLESS YOU ARE SURE THAT YOU KNOW WHAT YOU ARE DOING
 *  @generated
 */
#include "Calculator.h"

Calculator_add_args::~Calculator_add_args() throw() {}

uint32_t Calculator_add_args::read(::apache::thrift::protocol::TProtocol *iprot) {

    ::apache::thrift::protocol::TInputRecursionTracker tracker(*iprot);
    uint32_t xfer = 0;
    std::string fname;
    ::apache::thrift::protocol::TType ftype;
    int16_t fid;

    xfer += iprot->readStructBegin(fname);

    using ::apache::thrift::protocol::TProtocolException;

    while (true) {
        xfer += iprot->readFieldBegin(fname, ftype, fid);
        if (ftype == ::apache::thrift::protocol::T_STOP) {
            break;
        }
        switch (fid) {
        case 1:
            if (ftype == ::apache::thrift::protocol::T_I32) {
                xfer += iprot->readI32(this->num1);
                this->__isset.num1 = true;
            } else {
                xfer += iprot->skip(ftype);
            }
            break;
        case 2:
            if (ftype == ::apache::thrift::protocol::T_I32) {
                xfer += iprot->readI32(this->num2);
                this->__isset.num2 = true;
            } else {
                xfer += iprot->skip(ftype);
            }
            break;
        default:
            xfer += iprot->skip(ftype);
            break;
        }
        xfer += iprot->readFieldEnd();
    }

    xfer += iprot->readStructEnd();

    return xfer;
}

uint32_t Calculator_add_args::write(::apache::thrift::protocol::TProtocol *oprot) const {
    uint32_t xfer = 0;
    ::apache::thrift::protocol::TOutputRecursionTracker tracker(*oprot);
    xfer += oprot->writeStructBegin("Calculator_add_args");

    xfer += oprot->writeFieldBegin("num1", ::apache::thrift::protocol::T_I32, 1);
    xfer += oprot->writeI32(this->num1);
    xfer += oprot->writeFieldEnd();

    xfer += oprot->writeFieldBegin("num2", ::apache::thrift::protocol::T_I32, 2);
    xfer += oprot->writeI32(this->num2);
    xfer += oprot->writeFieldEnd();

    xfer += oprot->writeFieldStop();
    xfer += oprot->writeStructEnd();
    return xfer;
}

Calculator_add_pargs::~Calculator_add_pargs() throw() {}

uint32_t Calculator_add_pargs::write(::apache::thrift::protocol::TProtocol *oprot) const {
    uint32_t xfer = 0;
    ::apache::thrift::protocol::TOutputRecursionTracker tracker(*oprot);
    xfer += oprot->writeStructBegin("Calculator_add_pargs");

    xfer += oprot->writeFieldBegin("num1", ::apache::thrift::protocol::T_I32, 1);
    xfer += oprot->writeI32((*(this->num1)));
    xfer += oprot->writeFieldEnd();

    xfer += oprot->writeFieldBegin("num2", ::apache::thrift::protocol::T_I32, 2);
    xfer += oprot->writeI32((*(this->num2)));
    xfer += oprot->writeFieldEnd();

    xfer += oprot->writeFieldStop();
    xfer += oprot->writeStructEnd();
    return xfer;
}

Calculator_add_result::~Calculator_add_result() throw() {}

uint32_t Calculator_add_result::read(::apache::thrift::protocol::TProtocol *iprot) {

    ::apache::thrift::protocol::TInputRecursionTracker tracker(*iprot);
    uint32_t xfer = 0;
    std::string fname;
    ::apache::thrift::protocol::TType ftype;
    int16_t fid;

    xfer += iprot->readStructBegin(fname);

    using ::apache::thrift::protocol::TProtocolException;

    while (true) {
        xfer += iprot->readFieldBegin(fname, ftype, fid);
        if (ftype == ::apache::thrift::protocol::T_STOP) {
            break;
        }
        switch (fid) {
        case 0:
            if (ftype == ::apache::thrift::protocol::T_I64) {
                xfer += iprot->readI64(this->success);
                this->__isset.success = true;
            } else {
                xfer += iprot->skip(ftype);
            }
            break;
        default:
            xfer += iprot->skip(ftype);
            break;
        }
        xfer += iprot->readFieldEnd();
    }

    xfer += iprot->readStructEnd();

    return xfer;
}

uint32_t Calculator_add_result::write(::apache::thrift::protocol::TProtocol *oprot) const {

    uint32_t xfer = 0;

    xfer += oprot->writeStructBegin("Calculator_add_result");

    if (this->__isset.success) {
        xfer += oprot->writeFieldBegin("success", ::apache::thrift::protocol::T_I64, 0);
        xfer += oprot->writeI64(this->success);
        xfer += oprot->writeFieldEnd();
    }
    xfer += oprot->writeFieldStop();
    xfer += oprot->writeStructEnd();
    return xfer;
}

Calculator_add_presult::~Calculator_add_presult() throw() {}

uint32_t Calculator_add_presult::read(::apache::thrift::protocol::TProtocol *iprot) {

    ::apache::thrift::protocol::TInputRecursionTracker tracker(*iprot);
    uint32_t xfer = 0;
    std::string fname;
    ::apache::thrift::protocol::TType ftype;
    int16_t fid;

    xfer += iprot->readStructBegin(fname);

    using ::apache::thrift::protocol::TProtocolException;

    while (true) {
        xfer += iprot->readFieldBegin(fname, ftype, fid);
        if (ftype == ::apache::thrift::protocol::T_STOP) {
            break;
        }
        switch (fid) {
        case 0:
            if (ftype == ::apache::thrift::protocol::T_I64) {
                xfer += iprot->readI64((*(this->success)));
                this->__isset.success = true;
            } else {
                xfer += iprot->skip(ftype);
            }
            break;
        default:
            xfer += iprot->skip(ftype);
            break;
        }
        xfer += iprot->readFieldEnd();
    }

    xfer += iprot->readStructEnd();

    return xfer;
}

int64_t CalculatorClient::add(const int32_t num1, const int32_t num2) {
    send_add(num1, num2);
    return recv_add();
}

void CalculatorClient::send_add(const int32_t num1, const int32_t num2) {
    int32_t cseqid = 0;
    oprot_->writeMessageBegin("add", ::apache::thrift::protocol::T_CALL, cseqid);

    Calculator_add_pargs args;
    args.num1 = &num1;
    args.num2 = &num2;
    args.write(oprot_);

    oprot_->writeMessageEnd();
    oprot_->getTransport()->writeEnd();
    oprot_->getTransport()->flush();
}

int64_t CalculatorClient::recv_add() {

    int32_t rseqid = 0;
    std::string fname;
    ::apache::thrift::protocol::TMessageType mtype;

    iprot_->readMessageBegin(fname, mtype, rseqid);
    if (mtype == ::apache::thrift::protocol::T_EXCEPTION) {
        ::apache::thrift::TApplicationException x;
        x.read(iprot_);
        iprot_->readMessageEnd();
        iprot_->getTransport()->readEnd();
        throw x;
    }
    if (mtype != ::apache::thrift::protocol::T_REPLY) {
        iprot_->skip(::apache::thrift::protocol::T_STRUCT);
        iprot_->readMessageEnd();
        iprot_->getTransport()->readEnd();
    }
    if (fname.compare("add") != 0) {
        iprot_->skip(::apache::thrift::protocol::T_STRUCT);
        iprot_->readMessageEnd();
        iprot_->getTransport()->readEnd();
    }
    int64_t _return;
    Calculator_add_presult result;
    result.success = &_return;
    result.read(iprot_);
    iprot_->readMessageEnd();
    iprot_->getTransport()->readEnd();

    if (result.__isset.success) {
        return _return;
    }
    throw ::apache::thrift::TApplicationException(
        ::apache::thrift::TApplicationException::MISSING_RESULT, "add failed: unknown result");
}

bool CalculatorProcessor::dispatchCall(::apache::thrift::protocol::TProtocol *iprot,
                                       ::apache::thrift::protocol::TProtocol *oprot,
                                       const std::string &fname, int32_t seqid, void *callContext) {
    ProcessMap::iterator pfn;
    pfn = processMap_.find(fname);
    if (pfn == processMap_.end()) {
        iprot->skip(::apache::thrift::protocol::T_STRUCT);
        iprot->readMessageEnd();
        iprot->getTransport()->readEnd();
        ::apache::thrift::TApplicationException x(
            ::apache::thrift::TApplicationException::UNKNOWN_METHOD,
            "Invalid method name: '" + fname + "'");
        oprot->writeMessageBegin(fname, ::apache::thrift::protocol::T_EXCEPTION, seqid);
        x.write(oprot);
        oprot->writeMessageEnd();
        oprot->getTransport()->writeEnd();
        oprot->getTransport()->flush();
        return true;
    }
    (this->*(pfn->second))(seqid, iprot, oprot, callContext);
    return true;
}

void CalculatorProcessor::process_add(int32_t seqid, ::apache::thrift::protocol::TProtocol *iprot,
                                      ::apache::thrift::protocol::TProtocol *oprot,
                                      void *callContext) {
    void *ctx = NULL;
    if (this->eventHandler_.get() != NULL) {
        ctx = this->eventHandler_->getContext("Calculator.add", callContext);
    }
    ::apache::thrift::TProcessorContextFreer freer(this->eventHandler_.get(), ctx,
                                                   "Calculator.add");

    if (this->eventHandler_.get() != NULL) {
        this->eventHandler_->preRead(ctx, "Calculator.add");
    }

    Calculator_add_args args;
    args.read(iprot);
    iprot->readMessageEnd();
    uint32_t bytes = iprot->getTransport()->readEnd();

    if (this->eventHandler_.get() != NULL) {
        this->eventHandler_->postRead(ctx, "Calculator.add", bytes);
    }

    Calculator_add_result result;
    try {
        result.success = iface_->add(args.num1, args.num2);
        result.__isset.success = true;
    } catch (const std::exception &e) {
        if (this->eventHandler_.get() != NULL) {
            this->eventHandler_->handlerError(ctx, "Calculator.add");
        }

        ::apache::thrift::TApplicationException x(e.what());
        oprot->writeMessageBegin("add", ::apache::thrift::protocol::T_EXCEPTION, seqid);
        x.write(oprot);
        oprot->writeMessageEnd();
        oprot->getTransport()->writeEnd();
        oprot->getTransport()->flush();
        return;
    }

    if (this->eventHandler_.get() != NULL) {
        this->eventHandler_->preWrite(ctx, "Calculator.add");
    }

    oprot->writeMessageBegin("add", ::apache::thrift::protocol::T_REPLY, seqid);
    result.write(oprot);
    oprot->writeMessageEnd();
    bytes = oprot->getTransport()->writeEnd();
    oprot->getTransport()->flush();

    if (this->eventHandler_.get() != NULL) {
        this->eventHandler_->postWrite(ctx, "Calculator.add", bytes);
    }
}

::std::shared_ptr<::apache::thrift::TProcessor>
CalculatorProcessorFactory::getProcessor(const ::apache::thrift::TConnectionInfo &connInfo) {
    ::apache::thrift::ReleaseHandler<CalculatorIfFactory> cleanup(handlerFactory_);
    ::std::shared_ptr<CalculatorIf> handler(handlerFactory_->getHandler(connInfo), cleanup);
    ::std::shared_ptr<::apache::thrift::TProcessor> processor(new CalculatorProcessor(handler));
    return processor;
}

int64_t CalculatorConcurrentClient::add(const int32_t num1, const int32_t num2) {
    int32_t seqid = send_add(num1, num2);
    return recv_add(seqid);
}

int32_t CalculatorConcurrentClient::send_add(const int32_t num1, const int32_t num2) {
    int32_t cseqid = this->sync_.generateSeqId();
    ::apache::thrift::async::TConcurrentSendSentry sentry(&this->sync_);
    oprot_->writeMessageBegin("add", ::apache::thrift::protocol::T_CALL, cseqid);

    Calculator_add_pargs args;
    args.num1 = &num1;
    args.num2 = &num2;
    args.write(oprot_);

    oprot_->writeMessageEnd();
    oprot_->getTransport()->writeEnd();
    oprot_->getTransport()->flush();

    sentry.commit();
    return cseqid;
}

int64_t CalculatorConcurrentClient::recv_add(const int32_t seqid) {

    int32_t rseqid = 0;
    std::string fname;
    ::apache::thrift::protocol::TMessageType mtype;

    // the read mutex gets dropped and reacquired as part of waitForWork()
    // The destructor of this sentry wakes up other clients
    ::apache::thrift::async::TConcurrentRecvSentry sentry(&this->sync_, seqid);

    while (true) {
        if (!this->sync_.getPending(fname, mtype, rseqid)) {
            iprot_->readMessageBegin(fname, mtype, rseqid);
        }
        if (seqid == rseqid) {
            if (mtype == ::apache::thrift::protocol::T_EXCEPTION) {
                ::apache::thrift::TApplicationException x;
                x.read(iprot_);
                iprot_->readMessageEnd();
                iprot_->getTransport()->readEnd();
                sentry.commit();
                throw x;
            }
            if (mtype != ::apache::thrift::protocol::T_REPLY) {
                iprot_->skip(::apache::thrift::protocol::T_STRUCT);
                iprot_->readMessageEnd();
                iprot_->getTransport()->readEnd();
            }
            if (fname.compare("add") != 0) {
                iprot_->skip(::apache::thrift::protocol::T_STRUCT);
                iprot_->readMessageEnd();
                iprot_->getTransport()->readEnd();

                // in a bad state, don't commit
                using ::apache::thrift::protocol::TProtocolException;
                throw TProtocolException(TProtocolException::INVALID_DATA);
            }
            int64_t _return;
            Calculator_add_presult result;
            result.success = &_return;
            result.read(iprot_);
            iprot_->readMessageEnd();
            iprot_->getTransport()->readEnd();

            if (result.__isset.success) {
                sentry.commit();
                return _return;
            }
            // in a bad state, don't commit
            throw ::apache::thrift::TApplicationException(
                ::apache::thrift::TApplicationException::MISSING_RESULT,
                "add failed: unknown result");
        }
        // seqid != rseqid
        this->sync_.updatePending(fname, mtype, rseqid);

        // this will temporarily unlock the readMutex, and let other clients get work done
        this->sync_.waitForWork(seqid);
    } // end while(true)
}
